// authbc-delay.cc — AUTHBC delivery-delay scenario (item D3, and the direct test of C1).
//
// WHY THIS EXISTS. `models.energy.freshness_delay_s` predicts D(b) = fill + airtime + M/M/1
// queueing and has **no DCF channel-access term**: the wait for a contended medium is simply not
// modelled (docs/OPEN_ITEMS C1). The thesis says D(b) is therefore "a lower bound, credible only
// at low U" — a claim that was never tested. This scenario tests it.
//
// It differs from authbc-sat.cc in the one way that matters: the senders are **NOT saturated**.
// Saturation is right for a Bianchi throughput comparison and useless for delay, because an
// always-backlogged queue makes queueing delay diverge by construction. Here each node offers a
// specified load, so the channel runs at a chosen utilisation U and the measured delay is what a
// real deployment at that U would see.
//
// MEASUREMENT. Each frame is timestamped when the application hands it to the socket — i.e. on
// entering the MAC queue — and the delay is read at the receiving sink. So the measured quantity
// is exactly queueing + channel access + airtime + propagation, which is what D(b) claims to
// bound. Delivered fraction is reported alongside, because broadcast has no ARQ and a saturated
// channel loses frames rather than delaying them.
//
// Broadcast only: that is the AUTHBC traffic pattern (docs/02 §6a), and unicast ARQ would conflate
// retransmission with access delay.

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include <cmath>
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/packet-socket-address.h"
#include "ns3/packet-socket-helper.h"
#include "ns3/wifi-module.h"

#include <algorithm>
#include <fstream>
#include <map>
#include <numeric>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("AuthbcDelay");

// Per-frame send times, keyed by packet UID. NS-3 preserves the UID across the copies broadcast
// delivers, so one TX maps to many RX and each receiver's delay is recorded independently.
static std::map<uint64_t, double> g_txTime;
static std::vector<double> g_delays;      // seconds, one entry per (frame, receiver)
static uint64_t g_txCount = 0;
static uint64_t g_rxCount = 0;

void
AppTxTrace(Ptr<const Packet> p)
{
    g_txTime[p->GetUid()] = Simulator::Now().GetSeconds();
    ++g_txCount;
}

void
SinkRxTrace(Ptr<const Packet> p, const Address&)
{
    auto it = g_txTime.find(p->GetUid());
    if (it != g_txTime.end())
    {
        g_delays.push_back(Simulator::Now().GetSeconds() - it->second);
        ++g_rxCount;
    }
}

static double
Percentile(std::vector<double>& v, double q)
{
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    const double pos = q * (static_cast<double>(v.size()) - 1.0);
    const size_t lo = static_cast<size_t>(std::floor(pos));
    const size_t hi = static_cast<size_t>(std::ceil(pos));
    return (lo == hi) ? v[lo] : v[lo] + (pos - lo) * (v[hi] - v[lo]);
}

int
main(int argc, char* argv[])
{
    uint32_t nNodes = 50;
    uint32_t frameSize = 288;     // the optimized frame: H_f 44 + g_a 64 + 4x45 (docs/02 §7a)
    double simTime = 20.0;
    uint32_t seed = 1;
    std::string outPrefix = "ns3_delay";
    double framesPerSec = 5.0;    // per node: Lambda/b = 20/4 at the reference operating point

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "number of nodes in the collision domain", nNodes);
    cmd.AddValue("frameSize", "MAC payload bytes", frameSize);
    cmd.AddValue("simTime", "simulated seconds", simTime);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.AddValue("framesPerSec", "per-node offered frame rate (Lambda/b)", framesPerSec);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    NodeContainer nodes;
    nodes.Create(nNodes);

    // Same equal-power single collision domain as the Bianchi scenario, for the same reason:
    // every node must contend with every other, with no capture and no spatial reuse.
    YansWifiChannelHelper channel;
    channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
    channel.AddPropagationLoss("ns3::LogDistancePropagationLossModel", "Exponent", DoubleValue(0.0));
    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211a);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode", StringValue("OfdmRate6Mbps"),
                                 "ControlMode", StringValue("OfdmRate6Mbps"));
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    NetDeviceContainer devices = wifi.Install(phy, mac, nodes);
    Config::Set("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/RemoteStationManager/RtsCtsThreshold",
                UintegerValue(4692480)); // RTS/CTS off

    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    for (uint32_t i = 0; i < nNodes; ++i) posAlloc->Add(Vector(i * 0.01, 0.0, 0.0));
    mobility.SetPositionAllocator(posAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(nodes);

    PacketSocketHelper packetSocket;
    packetSocket.Install(nodes);
    const uint16_t protocol = 1;

    ApplicationContainer sinkApps, srcApps;
    for (uint32_t j = 0; j < nNodes; ++j)
    {
        PacketSocketAddress local;
        local.SetSingleDevice(devices.Get(j)->GetIfIndex());
        local.SetPhysicalAddress(devices.Get(j)->GetAddress());
        local.SetProtocol(protocol);
        PacketSinkHelper sink("ns3::PacketSocketFactory", Address(local));
        sinkApps.Add(sink.Install(nodes.Get(j)));
    }

    // Offered load per node = framesPerSec x frameSize. OnOff with a constant On period emits at
    // exactly DataRate, so the source is periodic rather than Poisson: that is the telemetry
    // pattern (a sensor sampling at Lambda), not an arbitrary arrival process.
    const uint64_t bps = static_cast<uint64_t>(framesPerSec * frameSize * 8.0);
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        PacketSocketAddress dest;
        dest.SetSingleDevice(devices.Get(i)->GetIfIndex());
        dest.SetPhysicalAddress(devices.Get(i)->GetBroadcast());
        dest.SetProtocol(protocol);
        OnOffHelper onoff("ns3::PacketSocketFactory", Address(dest));
        onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
        onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
        onoff.SetAttribute("DataRate", DataRateValue(DataRate(bps)));
        onoff.SetAttribute("PacketSize", UintegerValue(frameSize));
        srcApps.Add(onoff.Install(nodes.Get(i)));
    }

    // De-synchronise the sources: identical start times would make every node's periodic
    // transmission collide deterministically, which is an artifact, not DCF behaviour.
    Ptr<UniformRandomVariable> jitter = CreateObject<UniformRandomVariable>();
    jitter->SetAttribute("Min", DoubleValue(0.0));
    jitter->SetAttribute("Max", DoubleValue(1.0 / framesPerSec));
    for (uint32_t i = 0; i < srcApps.GetN(); ++i)
    {
        srcApps.Get(i)->SetStartTime(Seconds(1.0 + jitter->GetValue()));
        srcApps.Get(i)->SetStopTime(Seconds(1.0 + simTime));
    }
    // Sinks stop WITH the sources (audit F8): a longer-lived sink credits post-source drain.
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(1.0 + simTime));

    for (uint32_t i = 0; i < srcApps.GetN(); ++i)
        srcApps.Get(i)->TraceConnectWithoutContext("Tx", MakeCallback(&AppTxTrace));
    for (uint32_t i = 0; i < sinkApps.GetN(); ++i)
        sinkApps.Get(i)->TraceConnectWithoutContext("Rx", MakeCallback(&SinkRxTrace));

    Simulator::Stop(Seconds(2.0 + simTime));
    Simulator::Run();

    const double mean = g_delays.empty() ? 0.0
        : std::accumulate(g_delays.begin(), g_delays.end(), 0.0) / g_delays.size();
    // Each broadcast frame should be heard by (nNodes-1) peers; delivered fraction accounts for
    // collisions, which broadcast cannot retransmit away.
    const double expectedRx = static_cast<double>(g_txCount) * (nNodes - 1);
    std::ofstream out(outPrefix + ".csv");
    out << "key,value\n"
        << "nNodes," << nNodes << "\n"
        << "frameSize," << frameSize << "\n"
        << "framesPerSec," << framesPerSec << "\n"
        << "simTime," << simTime << "\n"
        << "seed," << seed << "\n"
        << "tx_frames," << g_txCount << "\n"
        << "rx_frames," << g_rxCount << "\n"
        << "delivered_frac," << (expectedRx > 0 ? g_rxCount / expectedRx : 0.0) << "\n"
        << "delay_mean_ms," << mean * 1e3 << "\n"
        << "delay_p50_ms," << Percentile(g_delays, 0.50) * 1e3 << "\n"
        << "delay_p95_ms," << Percentile(g_delays, 0.95) * 1e3 << "\n"
        << "delay_p99_ms," << Percentile(g_delays, 0.99) * 1e3 << "\n"
        << "delay_max_ms," << (g_delays.empty() ? 0.0 : *std::max_element(g_delays.begin(), g_delays.end())) * 1e3 << "\n";
    out.close();
    Simulator::Destroy();
    return 0;
}
