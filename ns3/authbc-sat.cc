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

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "number of nodes", nNodes);
    cmd.AddValue("mode", "unicast | broadcast", mode);
    cmd.AddValue("frameSize", "MAC payload bytes (== Bianchi L)", frameSize);
    cmd.AddValue("simTime", "simulated seconds", simTime);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.AddValue("offeredRate", "per-node offered load", offeredRate);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    NodeContainer nodes;
    nodes.Create(nNodes);

    YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
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

    // ONE collision domain: co-locate all nodes in a ~0.5 m cluster (1 cm spacing).
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        posAlloc->Add(Vector(i * 0.01, 0.0, 0.0));
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

    srcApps.Start(Seconds(1.0));
    srcApps.Stop(Seconds(simTime + 1.0));
    sinkApps.Start(Seconds(0.5));
    sinkApps.Stop(Seconds(simTime + 1.5));

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
          << "goodput_mbps," << goodputMbps << "\n";
    stats.close();

    Simulator::Destroy();
    return 0;
}
