// authbc-sat.cc — AUTHBC saturated-802.11a scenario for Bianchi validation (docs/04 §3, docs/06 §2).
//
// 802.11a ad-hoc, ConstantRateWifiManager @ OfdmRate6Mbps, RTS/CTS off, N saturated senders.
// TWO modes, each compared ONLY to its matching analytic variant (never mixed — docs/06 §2):
//   --mode=unicast   : node i -> node (i+1)%N, WITH ACKs  -> classic (ACK) Bianchi
//   --mode=broadcast : all -> subnet broadcast, NO ACK/retry -> the no-ACK Bianchi variant
// Frame application payload is a parameter (--frameSize); real sizes come from framesizes.csv at
// P6b. Goodput is measured at PacketSinks (app-level Rx); unicast also serializes FlowMonitor.
//
// Copy into the ns-3.41 scratch/ dir and run via `./ns3 run "authbc-sat --mode=..."`.

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/wifi-module.h"

#include <fstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("AuthbcSat");

int
main(int argc, char* argv[])
{
    uint32_t nNodes = 2;
    std::string mode = "unicast";
    uint32_t frameSize = 200; // application payload bytes
    double simTime = 30.0;
    uint32_t seed = 1;
    std::string outPrefix = "ns3_out";
    std::string offeredRate = "12Mbps"; // per-node offered load >> capacity => saturation

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "number of nodes", nNodes);
    cmd.AddValue("mode", "unicast | broadcast", mode);
    cmd.AddValue("frameSize", "application payload bytes", frameSize);
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

    // RTS/CTS off (high threshold)
    Config::Set("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/RemoteStationManager/RtsCtsThreshold",
                UintegerValue(4692480));

    // single collision domain: nodes 1 m apart, constant position
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    for (uint32_t i = 0; i < nNodes; ++i)
    {
        posAlloc->Add(Vector(i * 1.0, 0.0, 0.0));
    }
    mobility.SetPositionAllocator(posAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(nodes);

    InternetStackHelper stack;
    stack.Install(nodes);
    Ipv4AddressHelper address;
    address.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer ifaces = address.Assign(devices);

    const uint16_t port = 9;
    ApplicationContainer sinkApps;
    ApplicationContainer srcApps;

    auto makeSource = [&](uint32_t node, Address dest) {
        OnOffHelper onoff("ns3::UdpSocketFactory", dest);
        onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
        onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
        onoff.SetAttribute("DataRate", DataRateValue(DataRate(offeredRate)));
        onoff.SetAttribute("PacketSize", UintegerValue(frameSize));
        srcApps.Add(onoff.Install(nodes.Get(node)));
    };
    auto makeSink = [&](uint32_t node) {
        PacketSinkHelper sink("ns3::UdpSocketFactory",
                              InetSocketAddress(Ipv4Address::GetAny(), port));
        sinkApps.Add(sink.Install(nodes.Get(node)));
    };

    if (mode == "broadcast")
    {
        Ipv4Address bcast = ifaces.GetAddress(0).GetSubnetDirectedBroadcast("255.255.255.0");
        for (uint32_t i = 0; i < nNodes; ++i)
        {
            makeSink(i); // every node may receive broadcasts
            makeSource(i, InetSocketAddress(bcast, port));
        }
    }
    else // unicast
    {
        for (uint32_t i = 0; i < nNodes; ++i)
        {
            uint32_t dst = (i + 1) % nNodes;
            makeSink(dst);
            makeSource(i, InetSocketAddress(ifaces.GetAddress(dst), port));
        }
    }

    srcApps.Start(Seconds(1.0));
    srcApps.Stop(Seconds(simTime + 1.0));
    sinkApps.Start(Seconds(0.5));
    sinkApps.Stop(Seconds(simTime + 1.5));

    FlowMonitorHelper fmHelper;
    Ptr<FlowMonitor> monitor;
    if (mode == "unicast")
    {
        monitor = fmHelper.InstallAll();
    }

    Simulator::Stop(Seconds(simTime + 2.0));
    Simulator::Run();

    uint64_t rxBytes = 0;
    for (uint32_t i = 0; i < sinkApps.GetN(); ++i)
    {
        rxBytes += DynamicCast<PacketSink>(sinkApps.Get(i))->GetTotalRx();
    }
    double goodputMbps = (rxBytes * 8.0) / simTime / 1e6;

    std::ofstream stats(outPrefix + ".stats");
    stats << "key,value\n"
          << "mode," << mode << "\n"
          << "nNodes," << nNodes << "\n"
          << "frameSize," << frameSize << "\n"
          << "simTime," << simTime << "\n"
          << "seed," << seed << "\n"
          << "rx_bytes," << rxBytes << "\n"
          << "goodput_mbps," << goodputMbps << "\n";
    stats.close();

    if (mode == "unicast" && monitor)
    {
        monitor->SerializeToXmlFile(outPrefix + ".flowmon", false, false);
    }

    Simulator::Destroy();
    return 0;
}
