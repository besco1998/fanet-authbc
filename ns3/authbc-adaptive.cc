// authbc-adaptive.cc — revision A4: each node chooses its batch from the channel it hears
// (docs/AUTHBC Revision Plan.md A4; registration predictions/A4.md).
//
// WHY. The paper fixes b from the deadline (b <= 4 at 50 records/s and 100 ms) and shows what
// each fixed b costs and buys. A node does not know how many neighbours it has, but it can
// hear how busy the channel is. This scenario puts the paper's capacity model inside the
// sender: every control period (1 s) a node measures the share of time its radio found the
// channel busy with others' frames (rho_hat, from the PHY state trace), predicts the delivery
// of every batch size b = 1..b_max from the no-fit closed form of docs/02 §6g, and uses the
// SMALLEST b whose prediction clears 0.95 + margin — the freshest frame the channel allows.
//
//   prediction at b: rho_b = rho_hat * (f_b T_b) / (f_now T_now)   (all nodes alike)
//                    loss  = rho [1 - (1 - 1/W)^(rho/(1-rho))] + rho c / T_b
//   W = 16 (CWmin + 1), c = 8 us (twice the 4 us preamble-detection time), T = airtime + DIFS.
//
// Hysteresis: b moves one step per period, and only after two periods agree on the direction.
// A "manoeuvre" (Poisson, --manoeuvreRate per node per s) flushes the records gathered so far
// in a frame of their own, so a sharp change is not held back by the batch.
//
// The traffic is the published source's: Lambda = 50 records/s; a frame of b records is sent
// at a uniformly drawn instant of each frame period b/Lambda (authbc-delay.cc, J = one
// period). The frame of k records has the length the lean codec emits (146, 155, 164, 173 B
// for k = 1..4). Each frame carries its source, sequence number, record count and the time its
// newest record was taken in its first bytes, so receivers can count gaps and ages.
//
// Policies: adaptive (the controller), fixed (b = --fixedB throughout), oracle (knows the true
// number of nodes it contends with and applies the same model to it, without hysteresis).
//
// Scenarios: ramp — one collision domain at equal power (the published channel, FixedRss), the
// number of active nodes rising from --rampStart to --rampEnd over --rampSeconds; merge — two
// groups of --nNodes/2 in 50 m discs 3 km apart, B brought next to A at 60 s and taken away at
// 120 s, on A1's channel (free space, Nakagami-3, capture, 20 dBm); mobile — A1's group
// mobility at --speedMps.

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/packet-socket-address.h"
#include "ns3/packet-socket-helper.h"
#include "ns3/propagation-module.h"
#include "ns3/wifi-module.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <deque>
#include <fstream>
#include <map>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("AuthbcAdaptive");

namespace
{
const double kLambda = 50.0;                         // records/s
const uint32_t kBMax = 4;
const uint32_t kFrameBytes[kBMax + 1] = {0, 146, 155, 164, 173};
const double kW = 16.0;
const double kDetect = 8e-6;
const uint32_t kHeader = 4 + 4 + 1 + 8 + 8;          // src, seq, records, newest, sent

double
Airtime(uint32_t bytes)                              // authbc.models.bianchi.t_broadcast
{
    const double symbols = std::ceil((16.0 + 8.0 * (bytes + 36.0) + 6.0) / 24.0);
    return 20e-6 + symbols * 4e-6 + 34e-6;
}

double
PredictedDelivery(double rho, uint32_t b)
{
    if (rho >= 0.999) return 0.0;
    const double t = Airtime(kFrameBytes[b]);
    const double loss = rho * (1.0 - std::pow(1.0 - 1.0 / kW, rho / (1.0 - rho))) + rho * kDetect / t;
    return 1.0 - std::min(1.0, loss);
}

// the per-node airtime per second at batch b (records at Lambda)
double
Load(uint32_t b)
{
    return (kLambda / b) * Airtime(kFrameBytes[b]);
}

uint32_t
SmallestBatch(double rhoAt1, double target)
{
    // rhoAt1: the occupancy the node would see were every node at b = 1
    for (uint32_t b = 1; b <= kBMax; ++b)
    {
        if (PredictedDelivery(rhoAt1 * Load(b) / Load(1), b) >= target) return b;
    }
    return kBMax;
}

struct Global
{
    uint32_t n = 0;
    double dRef = 1e9;
    std::vector<Ptr<MobilityModel>> mob;
    std::vector<bool> active;
    // per control window (1 s): frames due and received among neighbours, for V(t)
    std::map<int64_t, uint64_t> windowDue, windowGot;
    std::map<int64_t, double> windowAgeSum;          // peak ages of receptions in the window
    std::map<int64_t, uint64_t> windowAgeCount;
    // peak age: per (source, receiver), newest-record time of the last frame received
    std::vector<double> lastNewest;
    std::vector<uint64_t> ageHist;                   // 1 ms bins
    uint64_t framesSent = 0, recordsSent = 0, bytesSent = 0, flushes = 0;
    uint64_t bChanges = 0;
} g;

double
Dist(uint32_t a, uint32_t b)
{
    return g.mob[a]->GetDistanceFrom(g.mob[b]);
}

class AdaptiveSource;
std::vector<Ptr<AdaptiveSource>> g_src;

class AdaptiveSource : public Application
{
  public:
    AdaptiveSource(Address dest, uint32_t node, std::string policy, uint32_t fixedB,
                   double margin, double manoeuvreRate)
        : m_dest(dest), m_node(node), m_policy(policy), m_b(policy == "fixed" ? fixedB : 1),
          m_margin(margin), m_manoeuvreRate(manoeuvreRate)
    {
        m_rand = CreateObject<UniformRandomVariable>();
        m_exp = CreateObject<ExponentialRandomVariable>();
    }

    void AddBusy(double seconds) { m_busy += seconds; }
    uint32_t Batch() const { return m_b; }

    // the oracle is told the true number of nodes it contends with
    void SetTrueContenders(uint32_t n) { m_trueContenders = n; }

  private:
    void StartApplication() override
    {
        m_socket = Socket::CreateSocket(GetNode(), PacketSocketFactory::GetTypeId());
        m_socket->Bind();
        m_socket->Connect(m_dest);
        g.active[m_node] = true;
        m_periodStart = Simulator::Now().GetSeconds();
        m_periodEvent = Simulator::Schedule(Seconds(m_b / kLambda), &AdaptiveSource::EndPeriod,
                                            this);
        m_controlEvent = Simulator::Schedule(Seconds(1.0), &AdaptiveSource::Control, this);
        if (m_manoeuvreRate > 0)
        {
            m_exp->SetAttribute("Mean", DoubleValue(1.0 / m_manoeuvreRate));
            m_manoeuvreEvent =
                Simulator::Schedule(Seconds(m_exp->GetValue()), &AdaptiveSource::Manoeuvre, this);
        }
    }

    void StopApplication() override
    {
        g.active[m_node] = false;
        m_stopped = true;                 // frames already scheduled are not sent
        Simulator::Cancel(m_periodEvent);
        Simulator::Cancel(m_controlEvent);
        Simulator::Cancel(m_manoeuvreEvent);
    }

    // The period's records are complete: schedule their frame at a uniform instant of the
    // next period (the published source), and start the next period at the current batch.
    void EndPeriod()
    {
        const double now = Simulator::Now().GetSeconds();
        const uint32_t k = static_cast<uint32_t>(std::lround((now - m_periodStart) * kLambda));
        const double period = m_b / kLambda;
        if (k >= 1)
        {
            const double at = m_rand->GetValue(0.0, period);
            Simulator::Schedule(Seconds(at), &AdaptiveSource::Send, this, std::min(k, kBMax),
                                now);
        }
        m_periodStart = now;
        m_periodEvent = Simulator::Schedule(Seconds(period), &AdaptiveSource::EndPeriod, this);
    }

    // A sharp change: the records gathered so far go now, in a frame of their own.
    void Manoeuvre()
    {
        const double now = Simulator::Now().GetSeconds();
        const uint32_t k = static_cast<uint32_t>(std::floor((now - m_periodStart) * kLambda));
        if (k >= 1)
        {
            ++g.flushes;
            Simulator::Cancel(m_periodEvent);
            Send(std::min(k, kBMax), now);
            m_periodStart = now;
            m_periodEvent = Simulator::Schedule(Seconds(m_b / kLambda),
                                                &AdaptiveSource::EndPeriod, this);
        }
        m_manoeuvreEvent =
            Simulator::Schedule(Seconds(m_exp->GetValue()), &AdaptiveSource::Manoeuvre, this);
    }

    void Send(uint32_t k, double newest)
    {
        if (m_stopped) return;
        std::vector<uint8_t> buf(kFrameBytes[k], 0);
        const uint32_t seq = m_seq++;
        const double now = Simulator::Now().GetSeconds();
        std::memcpy(buf.data(), &m_node, 4);
        std::memcpy(buf.data() + 4, &seq, 4);
        buf[8] = static_cast<uint8_t>(k);
        std::memcpy(buf.data() + 9, &newest, 8);
        std::memcpy(buf.data() + 17, &now, 8);
        Ptr<Packet> p = Create<Packet>(buf.data(), buf.size());
        ++g.framesSent;
        g.recordsSent += k;
        g.bytesSent += kFrameBytes[k];
        uint64_t due = 0;
        for (uint32_t r = 0; r < g.n; ++r)
            if (r != m_node && g.active[r] && Dist(m_node, r) <= g.dRef) ++due;
        g.windowDue[static_cast<int64_t>(now)] += due;
        m_socket->Send(p);
    }

    void Control()
    {
        // The radio is busy for a frame's airtime; the model's occupancy counts airtime + DIFS
        // per frame (T = t_broadcast). Convert by the current frame's ratio (all nodes alike).
        const double t = Airtime(kFrameBytes[m_b]);
        const double rho = (m_busy / 1.0) * t / (t - 34e-6);   // share of the last second
        m_busy = 0.0;
        uint32_t want = m_b;
        const double target = 0.95 + m_margin;
        if (m_policy == "adaptive")
        {
            // what the node would hear were every node at b = 1, from what it hears at m_b
            want = SmallestBatch(rho * Load(1) / Load(m_b), target);
        }
        else if (m_policy == "oracle")
        {
            const double rhoTrue = (m_trueContenders > 0 ? m_trueContenders : 0) * Load(1);
            want = SmallestBatch(rhoTrue, target);
        }
        if (m_policy == "adaptive")
        {
            const int dir = (want > m_b) - (want < m_b);
            if (dir != 0 && dir == m_lastDir)
            {
                m_b = static_cast<uint32_t>(static_cast<int>(m_b) + dir);
                ++g.bChanges;
                m_lastDir = 0;
            }
            else
            {
                m_lastDir = dir;
            }
        }
        else if (m_policy == "oracle" && want != m_b)
        {
            m_b = want;
            ++g.bChanges;
        }
        m_controlEvent = Simulator::Schedule(Seconds(1.0), &AdaptiveSource::Control, this);
    }

    Address m_dest;
    uint32_t m_node;
    std::string m_policy;
    uint32_t m_b;
    double m_margin;
    double m_manoeuvreRate;
    Ptr<UniformRandomVariable> m_rand;
    Ptr<ExponentialRandomVariable> m_exp;
    Ptr<Socket> m_socket;
    EventId m_periodEvent, m_controlEvent, m_manoeuvreEvent;
    bool m_stopped = false;
    double m_periodStart = 0.0;
    double m_busy = 0.0;
    uint32_t m_seq = 0;
    int m_lastDir = 0;
    uint32_t m_trueContenders = 0;
};

void
OnPhyState(uint32_t node, Time start, Time duration, WifiPhyState state)
{
    // busy with others' frames: sensed (CCA busy) or being received; own TX excluded
    if (state == WifiPhyState::CCA_BUSY || state == WifiPhyState::RX)
        g_src[node]->AddBusy(duration.GetSeconds());
}

void
OnReceive(uint32_t rx, Ptr<const Packet> p, const Address&)
{
    if (!g.active[rx] || p->GetSize() < kHeader) return;
    uint8_t hdr[kHeader];
    p->CopyData(hdr, kHeader);
    uint32_t src;
    double newest, sent;
    std::memcpy(&src, hdr, 4);
    std::memcpy(&newest, hdr + 9, 8);
    std::memcpy(&sent, hdr + 17, 8);
    if (src >= g.n || Dist(src, rx) > g.dRef) return;
    g.windowGot[static_cast<int64_t>(sent)] += 1;      // the window the frame was sent in
    double& last = g.lastNewest[static_cast<size_t>(src) * g.n + rx];
    if (last >= 0.0)
    {
        const double ageMs = (Simulator::Now().GetSeconds() - last) * 1e3;
        ++g.ageHist[std::min<uint32_t>(g.ageHist.size() - 1, static_cast<uint32_t>(ageMs))];
        g.windowAgeSum[static_cast<int64_t>(sent)] += ageMs;
        ++g.windowAgeCount[static_cast<int64_t>(sent)];
    }
    last = newest;
}

void
Relocate(NodeContainer nodes, uint32_t from, uint32_t to, Vector shift)
{
    for (uint32_t i = from; i < to; ++i)
    {
        Ptr<MobilityModel> m = nodes.Get(i)->GetObject<MobilityModel>();
        Vector p = m->GetPosition();
        m->SetPosition(Vector(p.x + shift.x, p.y + shift.y, p.z + shift.z));
    }
}

// The oracle's count: active nodes the node contends with (every active node in one
// collision domain; within the median preamble range, 582 m, on A1's channel).
void
CountContenders(bool spatial)
{
    for (uint32_t i = 0; i < g.n; ++i)
    {
        uint32_t c = 0;
        for (uint32_t j = 0; j < g.n; ++j)
            if (j != i && g.active[j] && (!spatial || Dist(i, j) <= 582.0)) ++c;
        g_src[i]->SetTrueContenders(c);
    }
    Simulator::Schedule(Seconds(0.25), &CountContenders, spatial);
}
} // namespace

int
main(int argc, char* argv[])
{
    std::string scenario = "ramp";
    std::string policy = "adaptive";
    uint32_t fixedB = 4;
    double margin = 0.01;
    uint32_t nNodes = 120;
    uint32_t rampStart = 20, rampEnd = 200;
    double rampSeconds = 120.0;
    double speedMps = 15.0;
    double manoeuvreRate = 0.0;
    double simTime = 130.0;
    double dRefM = 215.0;
    uint32_t seed = 1;
    std::string outPrefix = "adaptive";

    CommandLine cmd(__FILE__);
    cmd.AddValue("scenario", "ramp | merge | mobile", scenario);
    cmd.AddValue("policy", "adaptive | fixed | oracle", policy);
    cmd.AddValue("fixedB", "batch of the fixed policy", fixedB);
    cmd.AddValue("margin", "delivery the controller aims above 0.95", margin);
    cmd.AddValue("nNodes", "nodes (merge: both groups; mobile: the group)", nNodes);
    cmd.AddValue("rampStart", "active nodes at the start of the ramp", rampStart);
    cmd.AddValue("rampEnd", "active nodes at its end", rampEnd);
    cmd.AddValue("rampSeconds", "duration of the ramp", rampSeconds);
    cmd.AddValue("speedMps", "mean speed of the group (mobile)", speedMps);
    cmd.AddValue("manoeuvreRate", "manoeuvres per node per second (flush a partial frame)",
                 manoeuvreRate);
    cmd.AddValue("simTime", "simulated seconds after the 1 s start", simTime);
    cmd.AddValue("dRefM", "neighbour distance on the spatial channel", dRefM);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.Parse(argc, argv);
    NS_ABORT_MSG_IF(fixedB < 1 || fixedB > kBMax, "fixedB in 1..4");
    const bool spatial = scenario != "ramp";
    const uint32_t n = scenario == "ramp" ? rampEnd : nNodes;

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);
    g.n = n;
    g.dRef = spatial ? dRefM : 1e9;
    g.active.assign(n, false);
    g.lastNewest.assign(static_cast<size_t>(n) * n, -1.0);
    g.ageHist.assign(5000, 0);

    NodeContainer nodes;
    nodes.Create(n);
    YansWifiChannelHelper channel;
    channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    YansWifiPhyHelper phy;
    if (!spatial)
    {
        channel.AddPropagationLoss("ns3::FixedRssLossModel", "Rss", DoubleValue(-60.0));
    }
    else
    {
        channel.AddPropagationLoss("ns3::LogDistancePropagationLossModel", "Exponent",
                                   DoubleValue(2.0), "ReferenceDistance", DoubleValue(1.0),
                                   "ReferenceLoss", DoubleValue(46.7));
        channel.AddPropagationLoss("ns3::NakagamiPropagationLossModel", "m0", DoubleValue(3.0),
                                   "m1", DoubleValue(3.0), "m2", DoubleValue(3.0));
        phy.Set("TxPowerStart", DoubleValue(20.0));
        phy.Set("TxPowerEnd", DoubleValue(20.0));
    }
    phy.SetFrameCaptureModel("ns3::SimpleFrameCaptureModel", "Margin", DoubleValue(4.0));
    phy.SetChannel(channel.Create());
    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211a);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode",
                                 StringValue("OfdmRate6Mbps"), "ControlMode",
                                 StringValue("OfdmRate6Mbps"));
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    NetDeviceContainer devices = wifi.Install(phy, mac, nodes);
    Config::Set("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/RemoteStationManager/RtsCtsThreshold",
                UintegerValue(4692480));

    if (scenario == "mobile")
    {
        GroupMobilityHelper group;
        Ptr<GaussMarkovMobilityModel> ref = CreateObject<GaussMarkovMobilityModel>();
        ref->SetAttribute("Bounds", BoxValue(Box(-1000, 1000, -1000, 1000, 50, 150)));
        ref->SetAttribute("TimeStep", TimeValue(Seconds(0.5)));
        ref->SetAttribute("Alpha", DoubleValue(0.85));
        ref->SetAttribute("MeanVelocity", StringValue("ns3::ConstantRandomVariable[Constant=" +
                                                      std::to_string(speedMps) + "]"));
        ref->SetAttribute("MeanDirection",
                          StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"));
        ref->SetAttribute("MeanPitch", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
        ref->SetAttribute("NormalVelocity",
                          StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0|Bound=0]"));
        ref->SetAttribute("NormalDirection",
                          StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.2|Bound=0.4]"));
        ref->SetAttribute("NormalPitch",
                          StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0|Bound=0]"));
        ref->SetPosition(Vector(0.0, 0.0, 100.0));
        group.SetReferenceMobilityModel(ref);
        Ptr<ListPositionAllocator> offsets = CreateObject<ListPositionAllocator>();
        Ptr<UniformRandomVariable> u = CreateObject<UniformRandomVariable>();
        u->SetStream(4096);
        for (uint32_t i = 0; i < n; ++i)
            offsets->Add(Vector(u->GetValue(-60, 60), u->GetValue(-60, 60), u->GetValue(-50, 50)));
        group.SetMemberPositionAllocator(offsets);
        group.SetMemberMobilityModel("ns3::RandomWalk2dMobilityModel", "Bounds",
                                     RectangleValue(Rectangle(-60, 60, -60, 60)));
        group.Install(nodes);
        group.AssignStreams(nodes, 8192);
    }
    else
    {
        Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator>();
        Ptr<UniformRandomVariable> u = CreateObject<UniformRandomVariable>();
        u->SetStream(4096);
        for (uint32_t i = 0; i < n; ++i)
        {
            if (scenario == "ramp")
            {
                pos->Add(Vector(i * 0.01, 0.0, 0.0));
                continue;
            }
            // merge: group A (first half) round (0, 0), group B round (3000, 0)
            const double cx = i < n / 2 ? 0.0 : 3000.0;
            const double r = 50.0 * std::sqrt(u->GetValue(0.0, 1.0));
            const double a = u->GetValue(0.0, 2.0 * M_PI);
            pos->Add(Vector(cx + r * std::cos(a), r * std::sin(a), u->GetValue(50.0, 150.0)));
        }
        MobilityHelper mobility;
        mobility.SetPositionAllocator(pos);
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mobility.Install(nodes);
        if (scenario == "merge")
        {
            Simulator::Schedule(Seconds(1.0 + 60.0), &Relocate, nodes, n / 2, n,
                                Vector(-2900.0, 0.0, 0.0));
            Simulator::Schedule(Seconds(1.0 + 120.0), &Relocate, nodes, n / 2, n,
                                Vector(2900.0, 0.0, 0.0));
        }
    }
    for (uint32_t i = 0; i < n; ++i) g.mob.push_back(nodes.Get(i)->GetObject<MobilityModel>());

    PacketSocketHelper packetSocket;
    packetSocket.Install(nodes);
    ApplicationContainer sinkApps;
    for (uint32_t j = 0; j < n; ++j)
    {
        PacketSocketAddress local;
        local.SetSingleDevice(devices.Get(j)->GetIfIndex());
        local.SetPhysicalAddress(devices.Get(j)->GetAddress());
        local.SetProtocol(1);
        PacketSinkHelper sink("ns3::PacketSocketFactory", Address(local));
        sinkApps.Add(sink.Install(nodes.Get(j)));
        PacketSocketAddress dest;
        dest.SetSingleDevice(devices.Get(j)->GetIfIndex());
        dest.SetPhysicalAddress(devices.Get(j)->GetBroadcast());
        dest.SetProtocol(1);
        Ptr<AdaptiveSource> src =
            CreateObject<AdaptiveSource>(Address(dest), j, policy, fixedB, margin, manoeuvreRate);
        nodes.Get(j)->AddApplication(src);
        g_src.push_back(src);
        Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devices.Get(j));
        dev->GetPhy()->GetState()->TraceConnectWithoutContext("State",
                                                             MakeBoundCallback(&OnPhyState, j));
    }
    Ptr<UniformRandomVariable> start = CreateObject<UniformRandomVariable>();
    for (uint32_t i = 0; i < n; ++i)
    {
        double t0 = 1.0 + start->GetValue(0.0, 1.0 / kLambda);
        if (scenario == "ramp" && i >= rampStart)
            t0 += rampSeconds * (i - rampStart + 1) / static_cast<double>(rampEnd - rampStart);
        g_src[i]->SetStartTime(Seconds(t0));
        g_src[i]->SetStopTime(Seconds(1.0 + simTime));
    }
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(1.0 + simTime));
    for (uint32_t i = 0; i < n; ++i)
        sinkApps.Get(i)->TraceConnectWithoutContext("Rx", MakeBoundCallback(&OnReceive, i));
    if (policy == "oracle") Simulator::Schedule(Seconds(0.5), &CountContenders, spatial);

    // a time series: each second, the active nodes and their mean batch
    std::ofstream ts(outPrefix + "_ts.csv");
    ts << "t,active,mean_b,due,got,age_sum_ms,age_count\n";
    std::vector<std::pair<int64_t, std::pair<uint32_t, double>>> seriesNodes;
    for (int64_t s = 1; s <= static_cast<int64_t>(1.0 + simTime); ++s)
    {
        Simulator::Schedule(Seconds(s + 0.999), [s, &seriesNodes]() {
            uint32_t a = 0;
            double sb = 0.0;
            for (uint32_t i = 0; i < g.n; ++i)
                if (g.active[i])
                {
                    ++a;
                    sb += g_src[i]->Batch();
                }
            seriesNodes.push_back({s, {a, a ? sb / a : 0.0}});
        });
    }

    Simulator::Stop(Seconds(2.0 + simTime));
    Simulator::Run();

    for (const auto& [s, an] : seriesNodes)
        ts << s << "," << an.first << "," << an.second << "," << g.windowDue[s] << ","
           << g.windowGot[s] << "," << g.windowAgeSum[s] << "," << g.windowAgeCount[s] << "\n";
    ts.close();
    uint64_t ages = 0;
    double ageSum = 0.0;
    for (uint32_t b = 0; b < g.ageHist.size(); ++b)
    {
        ages += g.ageHist[b];
        ageSum += g.ageHist[b] * (b + 0.5);
    }
    auto pct = [&](double q) {
        const uint64_t want = static_cast<uint64_t>(std::ceil(q * ages));
        uint64_t acc = 0;
        for (uint32_t b = 0; b < g.ageHist.size(); ++b)
        {
            acc += g.ageHist[b];
            if (acc >= want && want > 0) return b + 1.0;
        }
        return 0.0;
    };
    std::ofstream out(outPrefix + ".csv");
    out << "key,value\n"
        << "frames_sent," << g.framesSent << "\n"
        << "records_sent," << g.recordsSent << "\n"
        << "bytes_per_record," << (g.recordsSent ? double(g.bytesSent) / g.recordsSent : 0) << "\n"
        << "flushes," << g.flushes << "\n"
        << "b_changes," << g.bChanges << "\n"
        << "peak_age_mean_ms," << (ages ? ageSum / ages : 0.0) << "\n"
        << "peak_age_p95_ms," << pct(0.95) << "\n"
        << "peak_age_p99_ms," << pct(0.99) << "\n";
    out.close();
    Simulator::Destroy();
    return 0;
}
