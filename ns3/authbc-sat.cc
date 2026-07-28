// authbc-sat.cc — AUTHBC saturated-802.11a scenario for Bianchi validation (docs/04 §3, docs/06 §2).
//
// 802.11a ad-hoc, ConstantRateWifiManager @ OfdmRate6Mbps, RTS/CTS off, N saturated senders,
// ALL co-located in ONE collision domain (required for the Bianchi comparison — a spread layout
// lets distant nodes reuse the channel and aggregate exceeds the 6 Mb/s PHY ceiling).
//
// Uses **PacketSocket** (raw 802.11 frames, NO IP/UDP/ARP) so the scenario is an artifact-free
// MAC-level Bianchi testbed: the MAC payload == --frameSize exactly, and unicast needs no ARP
// (which otherwise collapses at high N under saturation).
//
// TWO modes, each compared ONLY to its matching analytic variant (never mixed — docs/06 §2):
//   --mode=unicast   : node i -> node (i+1)%N MAC, WITH ACKs  -> classic (ACK) Bianchi
//   --mode=broadcast : all -> broadcast MAC, NO ACK/retry     -> the no-ACK Bianchi variant
// Broadcast is heard by all N-1 others in the single domain, so the analysis divides aggregate
// broadcast Rx by (N-1) to get channel goodput. Copy into scratch/ and run via `./ns3 run`.

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include <cmath>
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/packet-socket-address.h"
#include "ns3/packet-socket-helper.h"
#include "ns3/wifi-module.h"

#include <fstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("AuthbcSat");

// Total data frames handed to the PHY for transmission (PhyTxBegin) — lets us measure NS-3's
// REAL per-transmission success rate (delivered / transmitted) and compare it to the ideal
// binary-collision model's p_s: if NS-3 delivers far more, that is the capture effect.
static uint64_t g_txFrames = 0;

void
TxBeginTrace(Ptr<const Packet>, double)
{
    ++g_txFrames;
}

// Time node 0's PHY sensed the channel IDLE (backoff-able) — lets us recover the ACTUAL average
// slot duration and hence NS-3's true per-station tx probability τ, independent of the success
// rate. If τ tracks the constant 2/(W+1) but success exceeds (1−τ)^(N−1), the excess is capture;
// if τ itself drops with N, NS-3 broadcast adapts its access (not pure capture).
static double g_idleTimeS = 0.0;

void
PhyStateTrace(Time, Time duration, WifiPhyState state)
{
    if (state == WifiPhyState::IDLE)
    {
        g_idleTimeS += duration.GetSeconds();
    }
}

// Frames node 0's PHY started decoding but dropped (collisions/interference) — the direct
// per-receiver collision count for the capture study.
static uint64_t g_rxDrop = 0;

void
RxDropTrace(Ptr<const Packet>, WifiPhyRxfailureReason)
{
    ++g_rxDrop;
}

int
main(int argc, char* argv[])
{
    uint32_t nNodes = 2;
    std::string mode = "unicast";
    uint32_t frameSize = 200; // MAC payload bytes (== Bianchi L)
    double simTime = 30.0;
    uint32_t seed = 1;
    std::string outPrefix = "ns3_out";
    std::string offeredRate = "12Mbps"; // per-node offered load >> capacity => saturation
    bool capture = false;               // install a SimpleFrameCaptureModel (restart capture)
    bool equalPower = false;            // identical path loss on EVERY link (Bianchi assumption)
    bool realistic = false;             // FANET deployment scenario (Friis + 3D cluster + fading)
    double clusterM = 150.0;            // realistic-mode cluster radius, metres
    double nakagamiM = 0.0;             // >0 installs Nakagami fading with this m parameter
    double powerSpreadDb = 0.0;         // per-node tx-power spread so capture can act on collisions

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "number of nodes", nNodes);
    cmd.AddValue("mode", "unicast | broadcast", mode);
    cmd.AddValue("frameSize", "MAC payload bytes (== Bianchi L)", frameSize);
    cmd.AddValue("simTime", "simulated seconds", simTime);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.AddValue("offeredRate", "per-node offered load", offeredRate);
    cmd.AddValue("capture", "install SimpleFrameCaptureModel", capture);
    cmd.AddValue("equalPower", "constant path loss on every link (no near-far, no capture)", equalPower);
    cmd.AddValue("realistic", "FANET deployment scenario: Friis free-space + 3D cluster", realistic);
    cmd.AddValue("clusterM", "realistic-mode cluster radius in metres", clusterM);
    cmd.AddValue("nakagamiM", "realistic-mode Nakagami fading m (0 = none)", nakagamiM);
    cmd.AddValue("powerSpreadDb", "per-node tx power spread (dB, uniform)", powerSpreadDb);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    NodeContainer nodes;
    nodes.Create(nNodes);

    // Channel. DEFAULT (near-far): log-distance n=3 over the 1 cm-spaced line below gives a
    // ~50 dB spread between the nearest and farthest node -- ample for a receiver to CAPTURE
    // the strongest of several colliding frames. That violates the Bianchi assumption of
    // symmetric stations, so the analytic no-ACK model cannot be compared against it fairly.
    // --equalPower sets the path-loss exponent to 0: every link then has identical loss (L0),
    // i.e. all stations are electrically equidistant, capture is impossible, and the model is
    // tested on its own assumptions.
    YansWifiChannelHelper channel;
    if (realistic)
    {
        // DEPLOYMENT scenario. Air-to-air UAV links are line-of-sight, so free-space (Friis,
        // exponent 2) is the right model -- NOT the log-distance n=3 default, which describes
        // cluttered indoor/urban propagation and, with d0=1 m, even returns negative loss (gain)
        // for the sub-metre spacings used by the validation scenario. Optional Nakagami fading
        // models multipath/airframe shadowing (m=3 ~ strong LoS, m=1 ~ Rayleigh).
        channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
        channel.AddPropagationLoss("ns3::FriisPropagationLossModel",
                                   "Frequency", DoubleValue(5.18e9));
        if (nakagamiM > 0.0)
        {
            channel.AddPropagationLoss("ns3::NakagamiPropagationLossModel",
                                       "m0", DoubleValue(nakagamiM),
                                       "m1", DoubleValue(nakagamiM),
                                       "m2", DoubleValue(nakagamiM));
        }
    }
    else if (equalPower)
    {
        // Build from scratch: Default() would already have installed a log-distance model
        // and AddPropagationLoss CHAINS models (losses add), so we must not call it here.
        channel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
        channel.AddPropagationLoss("ns3::LogDistancePropagationLossModel",
                                   "Exponent", DoubleValue(0.0));
    }
    else
    {
        channel = YansWifiChannelHelper::Default();
    }
    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());
    if (capture)
    {
        phy.SetFrameCaptureModel("ns3::SimpleFrameCaptureModel");
    }

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

    // Optional per-node tx-power spread so frame capture has stronger/weaker frames to act on
    // (with equal power, capture is timing-only). Deterministic linear spread around 16 dBm.
    if (powerSpreadDb > 0.0 && nNodes > 1)
    {
        for (uint32_t i = 0; i < nNodes; ++i)
        {
            double dbm = 16.0 + powerSpreadDb * (static_cast<double>(i) / (nNodes - 1) - 0.5);
            Ptr<WifiPhy> p = DynamicCast<WifiNetDevice>(devices.Get(i))->GetPhy();
            p->SetAttribute("TxPowerStart", DoubleValue(dbm));
            p->SetAttribute("TxPowerEnd", DoubleValue(dbm));
        }
    }

    // ONE collision domain: co-locate all nodes in a ~0.5 m cluster (1 cm spacing).
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    if (realistic)
    {
        // A 3D UAV cluster: nodes on a spiral within clusterM radius at 50-120 m altitude, so
        // every pair is separated by tens of metres (link budget stays above 6 Mb/s sensitivity
        // out to ~300 m) and altitudes differ, as in a real formation.
        for (uint32_t i = 0; i < nNodes; ++i)
        {
            double frac = (nNodes > 1) ? double(i) / double(nNodes - 1) : 0.0;
            double ang = 2.0 * M_PI * 2.5 * frac;          // 2.5 turns
            double r = clusterM * std::sqrt(frac);         // area-uniform in the disc
            posAlloc->Add(Vector(r * std::cos(ang), r * std::sin(ang), 50.0 + 70.0 * frac));
        }
    }
    else
    {
        for (uint32_t i = 0; i < nNodes; ++i)
        {
            posAlloc->Add(Vector(i * 0.01, 0.0, 0.0));
        }
    }
    mobility.SetPositionAllocator(posAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(nodes);

    PacketSocketHelper packetSocket;
    packetSocket.Install(nodes);

    const uint16_t protocol = 1;
    ApplicationContainer sinkApps;
    ApplicationContainer srcApps;

    for (uint32_t j = 0; j < nNodes; ++j)
    {
        PacketSocketAddress local;
        local.SetSingleDevice(devices.Get(j)->GetIfIndex());
        local.SetPhysicalAddress(devices.Get(j)->GetAddress());
        local.SetProtocol(protocol);
        PacketSinkHelper sink("ns3::PacketSocketFactory", Address(local));
        sinkApps.Add(sink.Install(nodes.Get(j)));
    }

    for (uint32_t i = 0; i < nNodes; ++i)
    {
        Address destMac;
        if (mode == "broadcast")
        {
            destMac = devices.Get(i)->GetBroadcast();
        }
        else
        {
            destMac = devices.Get((i + 1) % nNodes)->GetAddress();
        }
        PacketSocketAddress dest;
        dest.SetSingleDevice(devices.Get(i)->GetIfIndex());
        dest.SetPhysicalAddress(destMac);
        dest.SetProtocol(protocol);

        OnOffHelper onoff("ns3::PacketSocketFactory", Address(dest));
        onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
        onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
        onoff.SetAttribute("DataRate", DataRateValue(DataRate(offeredRate)));
        onoff.SetAttribute("PacketSize", UintegerValue(frameSize));
        srcApps.Add(onoff.Install(nodes.Get(i)));
    }

    Config::ConnectWithoutContext(
        "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/PhyTxBegin", MakeCallback(&TxBeginTrace));
    Config::ConnectWithoutContext(
        "/NodeList/0/DeviceList/0/$ns3::WifiNetDevice/Phy/State/State", MakeCallback(&PhyStateTrace));
    Config::ConnectWithoutContext(
        "/NodeList/0/DeviceList/0/$ns3::WifiNetDevice/Phy/PhyRxDrop", MakeCallback(&RxDropTrace));

    // The sinks must stop WITH the sources, not after them. Under saturation the MAC queues are
    // backlogged (500 packets deep), so they keep draining at the full channel rate after the
    // sources stop; a sink that outlives them credits that extra airtime to rxBytes while the
    // goodput denominator is still simTime. Measured at N=50 broadcast: 0.5 s of drain on a 10 s
    // window = +5.4 % on every goodput number (docs/audits/p7.md, finding F8).
    srcApps.Start(Seconds(1.0));
    srcApps.Stop(Seconds(simTime + 1.0));
    sinkApps.Start(Seconds(0.5));
    sinkApps.Stop(Seconds(simTime + 1.0));

    Simulator::Stop(Seconds(simTime + 2.0));
    Simulator::Run();

    uint64_t rxBytes = 0;
    for (uint32_t i = 0; i < sinkApps.GetN(); ++i)
    {
        rxBytes += DynamicCast<PacketSink>(sinkApps.Get(i))->GetTotalRx();
    }
    // Broadcast is heard by all N-1 others in the single domain -> divide to get channel goodput.
    double rxScale = (mode == "broadcast" && nNodes > 1) ? (nNodes - 1.0) : 1.0;
    double goodputMbps = (rxBytes / rxScale) * 8.0 / simTime / 1e6;

    std::ofstream stats(outPrefix + ".stats");
    stats << "key,value\n"
          << "mode," << mode << "\n"
          << "nNodes," << nNodes << "\n"
          << "frameSize," << frameSize << "\n"
          << "simTime," << simTime << "\n"
          << "seed," << seed << "\n"
          << "rx_bytes," << rxBytes << "\n"
          << "rx_scale," << rxScale << "\n"
          << "tx_frames," << g_txFrames << "\n"
          << "idle_time_s," << g_idleTimeS << "\n"
          << "rx_drop_node0," << g_rxDrop << "\n"
          << "capture," << (capture ? 1 : 0) << "\n"
          << "power_spread_db," << powerSpreadDb << "\n"
          << "goodput_mbps," << goodputMbps << "\n";
    stats.close();

    Simulator::Destroy();
    return 0;
}
