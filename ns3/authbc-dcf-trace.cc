// authbc-dcf-trace.cc — INSTRUMENTED twin of authbc-sat.cc for the broadcast-residual study
// (docs/audits/p7.md "scenario-A broadcast residual"; docs/06 §2).
//
// WHY a separate file: authbc-sat.cc produced the frozen results/raw/ns3_matrix.csv and must stay
// byte-identical. This twin keeps the scenario (channel, MAC, apps, goodput accounting) EXACTLY the
// same and only ADDS trace output, so its goodput must reproduce the frozen matrix — that identity
// is the control that makes every trace-derived number attributable to the same experiment.
//
// What it measures, and why each is needed to discriminate the surviving hypotheses:
//   tx.csv  node,event(B|E),t_ns   — every PHY transmission start/end on EVERY node. Overlapping
//                                   transmissions form a "busy period"; its MULTIPLICITY (how many
//                                   stations transmitted into it) is the direct measurement of the
//                                   collision statistics that Bianchi predicts as Binomial(N, tau).
//   bo.csv  node,event(BO|CW),t_ns,value — every backoff draw and CW value, so tau and W are
//                                   MEASURED, not assumed (CLAUDE.md Law 2).
//   rx.csv  event,t_ns,reason      — node 0's PHY reception outcomes (begin/ok/drop+reason), which
//                                   separates "the frame was never lost" from "the model's slot
//                                   arithmetic is wrong".
//   .stats                         — goodput (identical accounting to authbc-sat.cc) plus the PHY
//                                   timing constants (SIFS, slot, ACK time, EIFS-no-DIFS) and MAC
//                                   contention parameters read back from the built objects.

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

NS_LOG_COMPONENT_DEFINE("AuthbcDcfTrace");

static std::ofstream g_txCsv;
static std::ofstream g_boCsv;
static std::ofstream g_rxCsv;
static uint64_t g_txFrames = 0;
static uint64_t g_rxBeginNode0 = 0;
static uint64_t g_rxOkNode0 = 0;
static uint64_t g_rxDropNode0 = 0;

// Trace hooks. Node id is bound at connect time (MakeBoundCallback) rather than parsed out of a
// Config path string — the object pointers are fetched directly, so no path can silently not match.
void
TxBegin(uint32_t node, Ptr<const Packet>, double)
{
    ++g_txFrames;
    g_txCsv << node << ",B," << Simulator::Now().GetNanoSeconds() << "\n";
}

void
TxEnd(uint32_t node, Ptr<const Packet>)
{
    g_txCsv << node << ",E," << Simulator::Now().GetNanoSeconds() << "\n";
}

void
BackoffDrawn(uint32_t node, uint32_t backoff, uint8_t)
{
    g_boCsv << node << ",BO," << Simulator::Now().GetNanoSeconds() << "," << backoff << "\n";
}

void
CwChanged(uint32_t node, uint32_t cw, uint8_t)
{
    g_boCsv << node << ",CW," << Simulator::Now().GetNanoSeconds() << "," << cw << "\n";
}

void
RxBeginNode0(Ptr<const Packet>, RxPowerWattPerChannelBand)
{
    ++g_rxBeginNode0;
    g_rxCsv << "begin," << Simulator::Now().GetNanoSeconds() << ",-\n";
}

void
RxOkNode0(Ptr<const Packet>)
{
    ++g_rxOkNode0;
    g_rxCsv << "ok," << Simulator::Now().GetNanoSeconds() << ",-\n";
}

void
RxDropNode0(Ptr<const Packet>, WifiPhyRxfailureReason reason)
{
    ++g_rxDropNode0;
    g_rxCsv << "drop," << Simulator::Now().GetNanoSeconds() << "," << reason << "\n";
}

int
main(int argc, char* argv[])
{
    uint32_t nNodes = 2;
    std::string mode = "broadcast";
    uint32_t frameSize = 1400;
    double simTime = 10.0;
    uint32_t seed = 1;
    std::string outPrefix = "dcf_out";
    std::string offeredRate = "12Mbps";
    bool equalPower = false;
    double powerSpreadDb = 0.0;
    bool traceEnabled = true;

    CommandLine cmd(__FILE__);
    cmd.AddValue("nNodes", "number of nodes", nNodes);
    cmd.AddValue("mode", "unicast | broadcast", mode);
    cmd.AddValue("frameSize", "MAC payload bytes (== Bianchi L)", frameSize);
    cmd.AddValue("simTime", "simulated seconds", simTime);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.AddValue("offeredRate", "per-node offered load", offeredRate);
    cmd.AddValue("equalPower", "constant path loss on every link (no near-far, no capture)",
                 equalPower);
    cmd.AddValue("powerSpreadDb", "per-node tx power spread (dB, uniform)", powerSpreadDb);
    cmd.AddValue("trace", "write the per-event CSV traces", traceEnabled);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    NodeContainer nodes;
    nodes.Create(nNodes);

    // --- channel: identical to authbc-sat.cc ------------------------------------------------
    YansWifiChannelHelper channel;
    if (equalPower)
    {
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

    // --- instrumentation --------------------------------------------------------------------
    if (traceEnabled)
    {
        g_txCsv.open(outPrefix + ".tx.csv");
        g_txCsv << "node,event,t_ns\n";
        g_boCsv.open(outPrefix + ".bo.csv");
        g_boCsv << "node,event,t_ns,value\n";
        g_rxCsv.open(outPrefix + ".rx.csv");
        g_rxCsv << "event,t_ns,reason\n";

        for (uint32_t i = 0; i < nNodes; ++i)
        {
            Ptr<WifiNetDevice> dev = DynamicCast<WifiNetDevice>(devices.Get(i));
            Ptr<WifiPhy> p = dev->GetPhy();
            p->TraceConnectWithoutContext("PhyTxBegin", MakeBoundCallback(&TxBegin, i));
            p->TraceConnectWithoutContext("PhyTxEnd", MakeBoundCallback(&TxEnd, i));
            Ptr<Txop> txop = dev->GetMac()->GetTxop();
            NS_ABORT_MSG_IF(!txop, "no non-QoS Txop on node " << i << " — scenario assumes DCF");
            txop->TraceConnectWithoutContext("BackoffTrace", MakeBoundCallback(&BackoffDrawn, i));
            txop->TraceConnectWithoutContext("CwTrace", MakeBoundCallback(&CwChanged, i));
        }
        Ptr<WifiPhy> p0 = DynamicCast<WifiNetDevice>(devices.Get(0))->GetPhy();
        p0->TraceConnectWithoutContext("PhyRxBegin", MakeCallback(&RxBeginNode0));
        p0->TraceConnectWithoutContext("PhyRxEnd", MakeCallback(&RxOkNode0));
        p0->TraceConnectWithoutContext("PhyRxDrop", MakeCallback(&RxDropNode0));
    }

    // Read the contention/timing parameters back OUT of the built objects instead of assuming
    // them (Law 2): these are the exact constants the analytic model must be compared against.
    Ptr<WifiNetDevice> dev0 = DynamicCast<WifiNetDevice>(devices.Get(0));
    Ptr<WifiPhy> phy0 = dev0->GetPhy();
    Ptr<Txop> txop0 = dev0->GetMac()->GetTxop();

    // Sinks stop WITH the sources — see the note in authbc-sat.cc (finding F8): a longer-lived
    // sink credits the post-source queue drain to rxBytes against an unchanged denominator.
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
    double rxScale = (mode == "broadcast" && nNodes > 1) ? (nNodes - 1.0) : 1.0;
    double goodputMbps = (rxBytes / rxScale) * 8.0 / simTime / 1e6;

    std::ofstream stats(outPrefix + ".stats");
    stats << "key,value\n"
          << "mode," << mode << "\n"
          << "nNodes," << nNodes << "\n"
          << "frameSize," << frameSize << "\n"
          << "simTime," << simTime << "\n"
          << "seed," << seed << "\n"
          << "equal_power," << (equalPower ? 1 : 0) << "\n"
          << "power_spread_db," << powerSpreadDb << "\n"
          << "rx_bytes," << rxBytes << "\n"
          << "rx_scale," << rxScale << "\n"
          << "tx_frames," << g_txFrames << "\n"
          << "rx_begin_node0," << g_rxBeginNode0 << "\n"
          << "rx_ok_node0," << g_rxOkNode0 << "\n"
          << "rx_drop_node0," << g_rxDropNode0 << "\n"
          << "goodput_mbps," << goodputMbps << "\n"
          << "sifs_ns," << phy0->GetSifs().GetNanoSeconds() << "\n"
          << "slot_ns," << phy0->GetSlot().GetNanoSeconds() << "\n"
          << "ack_tx_ns," << phy0->GetAckTxTime().GetNanoSeconds() << "\n"
          << "eifs_no_difs_ns,"
          << (phy0->GetSifs() + phy0->GetAckTxTime()).GetNanoSeconds() << "\n"
          << "cw_min," << txop0->GetMinCw() << "\n"
          << "cw_max," << txop0->GetMaxCw() << "\n"
          << "aifsn," << static_cast<uint32_t>(txop0->GetAifsn()) << "\n";
    stats.close();

    if (traceEnabled)
    {
        g_txCsv.close();
        g_boCsv.close();
        g_rxCsv.close();
    }

    Simulator::Destroy();
    return 0;
}
