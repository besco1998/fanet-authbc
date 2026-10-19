// authbc-spatial.cc — revision A1: the swarm spread out, with fading, capture, hidden stations
// and motion (docs/AUTHBC Revision Plan.md A1; registration predictions/A1.md).
//
// WHY A SECOND SCENARIO. Every capacity of the paper is of one collision domain at equal power
// (authbc-delay.cc). This file keeps that scenario's traffic source, MAC and PHY rate exactly,
// and changes what the plan's A1 changes: where the nodes are, how received power falls with
// distance, and what a receiver counts. authbc-delay.cc is not touched, so every published run
// stays reproducible bit for bit.
//
// GEOMETRY (--layout):
//   point     every node at one point; --fixedRssDbm gives every link that power. With the
//             published traffic source this must reproduce the published crossings (35 / 124):
//             the check that this code path did not move the baseline.
//   disc      S1: uniform in a disc of radius --radiusM, altitude uniform in [50, 150] m.
//   clusters  S2: --nNodes split into three groups of equal size in discs of radius
//             --clusterRadiusM at altitude 100 m: A centred at (-sep/2, 0), B at (+sep/2, 0),
//             M at the origin, sep = --separationM. A and B cannot always sense each other;
//             receivers in M hear both: the hidden-station case.
//   group     S3: one reference point under Gauss-Markov motion at --speedMps mean speed in a
//             2 km box, 50-150 m altitude; each member a random walk within +-60 m of it.
//             --speedMps 0 keeps the reference still (members still walk within the box).
//
// CHANNEL (every layout except point): log-distance, exponent 2, 46.7 dB at 1 m (free space at
// 5.2 GHz), then Nakagami m = 3 on every link; 20 dBm; frame capture with a 4 dB margin.
//
// WHAT IS COUNTED. A node r is a NEIGHBOUR of sender s for a frame if their distance when r
// receives (or, for frames r misses, when s hands the frame to its MAC) is at most --dRefM:
// the distance at which an isolated link delivers 99 % (measured first, --layout pair). V of a
// receiver is the share of its neighbours' frames it received. Peak age per neighbour pair:
// the time from a sender's frame leaving its application to the reception of that sender's
// NEXT frame at the receiver, written as a histogram. Every non-neighbour reception is counted
// apart, so nothing is lost from the books.

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
#include <deque>
#include <fstream>
#include <map>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("AuthbcSpatial");

namespace
{
uint32_t g_n = 0;
double g_dRef = 0.0;
double g_warmup = 1.0;                       // seconds: frames handed over before this are not
                                             // counted, as the published scenario's sources
                                             // start between 1 s and 1 s + one period
NodeContainer g_nodes;
std::vector<Ptr<MobilityModel>> g_mob;       // looked up once: Dist runs N^2 times a second
std::map<uint64_t, uint32_t> g_srcOf;        // packet uid -> source node
std::map<uint64_t, double> g_sentAt;         // packet uid -> application hand-over time
std::vector<uint64_t> g_tx;                  // frames handed over, per source
std::vector<uint64_t> g_expect;              // neighbour-frames due, per receiver
std::vector<uint64_t> g_got;                 // neighbour-frames received, per receiver
std::vector<uint64_t> g_neighbourSum;        // sum over frames of the sender's neighbour count
std::vector<uint64_t> g_rxAll;               // every reception, per receiver
uint64_t g_rxFar = 0;                        // receptions from beyond d_ref
// Peak age: per (source, receiver), when the source sent the last frame this receiver got.
std::vector<double> g_lastSent;
std::vector<uint32_t> g_pairGot;             // receptions per (source, receiver), every distance
std::vector<uint64_t> g_ageHist;             // 1 ms bins
const uint32_t kAgeBins = 5000;

double
Dist(uint32_t a, uint32_t b)
{
    return g_mob[a]->GetDistanceFrom(g_mob[b]);
}

void
OnSend(uint32_t src, Ptr<const Packet> p)
{
    const double now = Simulator::Now().GetSeconds();
    g_srcOf[p->GetUid()] = src;
    g_sentAt[p->GetUid()] = now;
    if (now < g_warmup) return;
    ++g_tx[src];
    uint64_t k = 0;
    for (uint32_t r = 0; r < g_n; ++r)
    {
        if (r == src) continue;
        if (Dist(src, r) <= g_dRef)
        {
            ++g_expect[r];
            ++k;
        }
    }
    g_neighbourSum[src] += k;
}

void
OnReceive(uint32_t rx, Ptr<const Packet> p, const Address&)
{
    auto it = g_srcOf.find(p->GetUid());
    if (it == g_srcOf.end()) return;
    const uint32_t src = it->second;
    const double sent = g_sentAt[p->GetUid()];
    if (sent < g_warmup) return;
    ++g_rxAll[rx];
    ++g_pairGot[static_cast<size_t>(src) * g_n + rx];
    if (Dist(src, rx) > g_dRef)
    {
        ++g_rxFar;
        return;
    }
    ++g_got[rx];
    double& last = g_lastSent[static_cast<size_t>(src) * g_n + rx];
    if (last >= 0.0)
    {
        const double ageMs = (Simulator::Now().GetSeconds() - last) * 1e3;
        ++g_ageHist[std::min<uint32_t>(kAgeBins - 1, static_cast<uint32_t>(ageMs))];
    }
    last = sent;
}

// The published scenario's jittered periodic source, unchanged (authbc-delay.cc), except that
// it reports its sends to OnSend.
class JitteredPeriodicSource : public Application
{
  public:
    JitteredPeriodicSource(Address dest, Time period, Time jitter, uint32_t pktSize,
                           uint32_t node)
        : m_dest(dest), m_period(period), m_jitter(jitter), m_pktSize(pktSize), m_node(node)
    {
        m_rand = CreateObject<UniformRandomVariable>();
    }

  private:
    void StartApplication() override
    {
        m_socket = Socket::CreateSocket(GetNode(), PacketSocketFactory::GetTypeId());
        m_socket->Bind();
        m_socket->Connect(m_dest);
        m_tick = Simulator::Schedule(m_period, &JitteredPeriodicSource::Tick, this);
    }

    void StopApplication() override
    {
        Simulator::Cancel(m_tick);
        for (auto& e : m_pending) Simulator::Cancel(e);
        m_pending.clear();
    }

    void Tick()
    {
        const Time extra = Seconds(m_rand->GetValue(0.0, m_jitter.GetSeconds()));
        m_pending.push_back(Simulator::Schedule(extra, &JitteredPeriodicSource::Send, this));
        m_tick = Simulator::Schedule(m_period, &JitteredPeriodicSource::Tick, this);
    }

    void Send()
    {
        m_pending.pop_front();
        Ptr<Packet> p = Create<Packet>(m_pktSize);
        OnSend(m_node, p);
        m_socket->Send(p);
    }

    Address m_dest;
    Time m_period;
    Time m_jitter;
    uint32_t m_pktSize;
    uint32_t m_node;
    Ptr<UniformRandomVariable> m_rand;
    Ptr<Socket> m_socket;
    EventId m_tick;
    std::deque<EventId> m_pending;
};

Ptr<ListPositionAllocator>
Placement(const std::string& layout, uint32_t n, double radiusM, double clusterRadiusM,
          double separationM, double pairDistanceM)
{
    Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator>();
    // A stream of its own, far from the automatic ones, as authbc-delay.cc does.
    Ptr<UniformRandomVariable> u = CreateObject<UniformRandomVariable>();
    u->SetStream(4096);
    auto inDisc = [&](double cx, double cy, double r, double zLo, double zHi) {
        const double rr = r * std::sqrt(u->GetValue(0.0, 1.0));
        const double a = u->GetValue(0.0, 2.0 * M_PI);
        pos->Add(Vector(cx + rr * std::cos(a), cy + rr * std::sin(a), u->GetValue(zLo, zHi)));
    };
    if (layout == "point")
    {
        for (uint32_t i = 0; i < n; ++i) pos->Add(Vector(i * 0.01, 0.0, 0.0));
    }
    else if (layout == "pair")
    {
        NS_ABORT_MSG_IF(n != 2, "the pair layout has two nodes");
        pos->Add(Vector(0.0, 0.0, 100.0));
        pos->Add(Vector(pairDistanceM, 0.0, 100.0));
    }
    else if (layout == "disc")
    {
        for (uint32_t i = 0; i < n; ++i) inDisc(0.0, 0.0, radiusM, 50.0, 150.0);
    }
    else if (layout == "clusters")
    {
        for (uint32_t i = 0; i < n; ++i)
        {
            const double cx = (i % 3 == 0) ? -separationM / 2 : (i % 3 == 1) ? separationM / 2 : 0;
            inDisc(cx, 0.0, clusterRadiusM, 100.0, 100.0);
        }
    }
    else
    {
        NS_ABORT_MSG("unknown layout " << layout);
    }
    return pos;
}
} // namespace

int
main(int argc, char* argv[])
{
    uint32_t nNodes = 50;
    uint32_t frameSize = 173;
    double framesPerSec = 12.5;
    double simTime = 20.0;
    uint32_t seed = 1;
    std::string outPrefix = "spatial";
    double txJitterMs = 0.0;           // 0: one full sending period, the published source
    std::string layout = "disc";
    double radiusM = 100.0;
    double clusterRadiusM = 30.0;
    double separationM = 440.0;
    double pairDistanceM = 100.0;
    double speedMps = 0.0;
    double fixedRssDbm = -60.0;
    double dRefM = 1e9;                // every node a neighbour unless set
    double nakagamiM = 3.0;            // 0 switches fading off (a diagnostic, not a scenario)
    double captureMarginDb = 4.0;      // < 0 removes the capture model
    bool pairs = false;                // also write <outPrefix>_pairs.csv (S2: links by class)

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "number of nodes", nNodes);
    cmd.AddValue("frameSize", "MAC payload bytes", frameSize);
    cmd.AddValue("framesPerSec", "per-node frame rate (Lambda/b)", framesPerSec);
    cmd.AddValue("simTime", "simulated seconds", simTime);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.AddValue("txJitterMs", "send jitter in ms; 0 = one full sending period", txJitterMs);
    cmd.AddValue("layout", "point | pair | disc | clusters | group", layout);
    cmd.AddValue("radiusM", "disc radius (disc)", radiusM);
    cmd.AddValue("clusterRadiusM", "cluster radius (clusters)", clusterRadiusM);
    cmd.AddValue("separationM", "distance between clusters A and B (clusters)", separationM);
    cmd.AddValue("pairDistanceM", "distance between the two nodes (pair)", pairDistanceM);
    cmd.AddValue("speedMps", "mean speed of the group's reference point (group)", speedMps);
    cmd.AddValue("fixedRssDbm", "received power of every link (point)", fixedRssDbm);
    cmd.AddValue("dRefM", "neighbour distance: an isolated link delivers 99 % within it", dRefM);
    cmd.AddValue("nakagamiM", "Nakagami m on every link; 0 = no fading", nakagamiM);
    cmd.AddValue("captureMarginDb", "frame-capture margin in dB; < 0 = no capture model",
                 captureMarginDb);
    cmd.AddValue("pairs", "also write receptions per (source, receiver) pair", pairs);
    cmd.Parse(argc, argv);
    const double period = 1.0 / framesPerSec;
    const double jitter = txJitterMs > 0.0 ? txJitterMs * 1e-3 : period;
    NS_ABORT_MSG_IF(jitter > period * (1 + 1e-12), "the jitter must not exceed one period");

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    g_n = nNodes;
    g_dRef = dRefM;
    g_nodes.Create(nNodes);
    g_tx.assign(nNodes, 0);
    g_expect.assign(nNodes, 0);
    g_got.assign(nNodes, 0);
    g_neighbourSum.assign(nNodes, 0);
    g_rxAll.assign(nNodes, 0);
    g_lastSent.assign(static_cast<size_t>(nNodes) * nNodes, -1.0);
    g_pairGot.assign(static_cast<size_t>(nNodes) * nNodes, 0);
    g_ageHist.assign(kAgeBins, 0);

    YansWifiChannelHelper channel;
    channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    YansWifiPhyHelper phy;
    if (layout == "point")
    {
        channel.AddPropagationLoss("ns3::FixedRssLossModel", "Rss", DoubleValue(fixedRssDbm));
    }
    else
    {
        channel.AddPropagationLoss("ns3::LogDistancePropagationLossModel",
                                   "Exponent", DoubleValue(2.0),
                                   "ReferenceDistance", DoubleValue(1.0),
                                   "ReferenceLoss", DoubleValue(46.7));
        if (nakagamiM > 0.0)
        {
            channel.AddPropagationLoss("ns3::NakagamiPropagationLossModel",
                                       "m0", DoubleValue(nakagamiM),
                                       "m1", DoubleValue(nakagamiM),
                                       "m2", DoubleValue(nakagamiM));
        }
        phy.Set("TxPowerStart", DoubleValue(20.0));
        phy.Set("TxPowerEnd", DoubleValue(20.0));
    }
    if (captureMarginDb >= 0.0)
    {
        phy.SetFrameCaptureModel("ns3::SimpleFrameCaptureModel", "Margin",
                                 DoubleValue(captureMarginDb));
    }
    phy.SetChannel(channel.Create());

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211a);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("OfdmRate6Mbps"),
                                 "ControlMode", StringValue("OfdmRate6Mbps"));
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    NetDeviceContainer devices = wifi.Install(phy, mac, g_nodes);
    Config::Set("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/RemoteStationManager/RtsCtsThreshold",
                UintegerValue(4692480));
    // Random streams are left to ns-3's automatic assignment, as in authbc-delay.cc: a run is a
    // function of (seed, arguments) because objects are created in a fixed order.

    if (layout == "group")
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
        for (uint32_t i = 0; i < nNodes; ++i)
            offsets->Add(Vector(u->GetValue(-60, 60), u->GetValue(-60, 60), u->GetValue(-50, 50)));
        group.SetMemberPositionAllocator(offsets);
        // Members keep station around the reference point with ns-3's default random walk
        // (2-4 m/s); at speed 0 the whole swarm is still, the control of the mobility sweep.
        if (speedMps > 0.0)
            group.SetMemberMobilityModel("ns3::RandomWalk2dMobilityModel",
                                         "Bounds", RectangleValue(Rectangle(-60, 60, -60, 60)));
        else
            group.SetMemberMobilityModel("ns3::ConstantPositionMobilityModel");
        group.Install(g_nodes);
        group.AssignStreams(g_nodes, 8192);
    }
    else
    {
        MobilityHelper mobility;
        mobility.SetPositionAllocator(Placement(layout, nNodes, radiusM, clusterRadiusM,
                                                separationM, pairDistanceM));
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mobility.Install(g_nodes);
    }
    for (uint32_t i = 0; i < nNodes; ++i) g_mob.push_back(g_nodes.Get(i)->GetObject<MobilityModel>());

    PacketSocketHelper packetSocket;
    packetSocket.Install(g_nodes);
    const uint16_t protocol = 1;
    ApplicationContainer sinkApps, srcApps;
    for (uint32_t j = 0; j < nNodes; ++j)
    {
        PacketSocketAddress local;
        local.SetSingleDevice(devices.Get(j)->GetIfIndex());
        local.SetPhysicalAddress(devices.Get(j)->GetAddress());
        local.SetProtocol(protocol);
        PacketSinkHelper sink("ns3::PacketSocketFactory", Address(local));
        sinkApps.Add(sink.Install(g_nodes.Get(j)));
    }
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        if (layout == "pair" && i == 1) continue;     // an isolated link: one sender
        PacketSocketAddress dest;
        dest.SetSingleDevice(devices.Get(i)->GetIfIndex());
        dest.SetPhysicalAddress(devices.Get(i)->GetBroadcast());
        dest.SetProtocol(protocol);
        Ptr<JitteredPeriodicSource> src = CreateObject<JitteredPeriodicSource>(
            Address(dest), Seconds(period), Seconds(jitter), frameSize, i);
        g_nodes.Get(i)->AddApplication(src);
        srcApps.Add(src);
    }
    Ptr<UniformRandomVariable> start = CreateObject<UniformRandomVariable>();
    start->SetAttribute("Min", DoubleValue(0.0));
    start->SetAttribute("Max", DoubleValue(period));
    for (uint32_t i = 0; i < srcApps.GetN(); ++i)
    {
        srcApps.Get(i)->SetStartTime(Seconds(1.0 + start->GetValue()));
        srcApps.Get(i)->SetStopTime(Seconds(1.0 + simTime));
    }
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(1.0 + simTime));
    for (uint32_t i = 0; i < sinkApps.GetN(); ++i)
        sinkApps.Get(i)->TraceConnectWithoutContext("Rx", MakeBoundCallback(&OnReceive, i));

    Simulator::Stop(Seconds(2.0 + simTime));
    Simulator::Run();

    // Summary: one key,value file, as authbc-delay.cc writes.
    uint64_t tx = 0, expect = 0, got = 0, rxAll = 0, nbSum = 0;
    double vSum = 0.0;
    uint32_t vCount = 0;
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        tx += g_tx[i];
        expect += g_expect[i];
        got += g_got[i];
        rxAll += g_rxAll[i];
        nbSum += g_neighbourSum[i];
        if (g_expect[i] > 0)
        {
            vSum += static_cast<double>(g_got[i]) / g_expect[i];
            ++vCount;
        }
    }
    uint64_t ages = 0;
    double ageSum = 0.0;
    for (uint32_t b = 0; b < kAgeBins; ++b)
    {
        ages += g_ageHist[b];
        ageSum += g_ageHist[b] * (b + 0.5);
    }
    auto agePct = [&](double q) {
        const uint64_t want = static_cast<uint64_t>(std::ceil(q * ages));
        uint64_t acc = 0;
        for (uint32_t b = 0; b < kAgeBins; ++b)
        {
            acc += g_ageHist[b];
            if (acc >= want && want > 0) return b + 1.0;      // upper edge of the bin
        }
        return 0.0;
    };
    std::ofstream out(outPrefix + ".csv");
    out << "key,value\n"
        << "nNodes," << nNodes << "\n"
        << "frameSize," << frameSize << "\n"
        << "framesPerSec," << framesPerSec << "\n"
        << "simTime," << simTime << "\n"
        << "seed," << seed << "\n"
        << "tx_frames," << tx << "\n"
        << "neighbour_frames_due," << expect << "\n"
        << "neighbour_frames_got," << got << "\n"
        << "v_pooled," << (expect ? static_cast<double>(got) / expect : 0.0) << "\n"
        << "v_mean_receiver," << (vCount ? vSum / vCount : 0.0) << "\n"
        << "receivers_with_neighbours," << vCount << "\n"
        << "mean_neighbours," << (tx ? static_cast<double>(nbSum) / tx : 0.0) << "\n"
        << "rx_all," << rxAll << "\n"
        << "rx_beyond_dref," << g_rxFar << "\n"
        << "age_samples," << ages << "\n"
        << "peak_age_mean_ms," << (ages ? ageSum / ages : 0.0) << "\n"
        << "peak_age_p95_ms," << agePct(0.95) << "\n"
        << "peak_age_p99_ms," << agePct(0.99) << "\n";
    out.close();
    // Positions at the end of the run, for the hidden-station share computed in the analysis
    // (static layouts: where the nodes were throughout).
    std::ofstream posOut(outPrefix + "_pos.csv");
    posOut << "node,x,y,z,tx,expect,got\n";
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        const Vector v = g_nodes.Get(i)->GetObject<MobilityModel>()->GetPosition();
        posOut << i << "," << v.x << "," << v.y << "," << v.z << "," << g_tx[i] << ","
               << g_expect[i] << "," << g_got[i] << "\n";
    }
    if (pairs)
    {
        std::ofstream pairOut(outPrefix + "_pairs.csv");
        pairOut << "src,rx,distance_m,src_tx,got\n";
        for (uint32_t s = 0; s < nNodes; ++s)
            for (uint32_t r = 0; r < nNodes; ++r)
                if (r != s)
                    pairOut << s << "," << r << "," << Dist(s, r) << "," << g_tx[s] << ","
                            << g_pairGot[static_cast<size_t>(s) * nNodes + r] << "\n";
    }
    Simulator::Destroy();
    return 0;
}
