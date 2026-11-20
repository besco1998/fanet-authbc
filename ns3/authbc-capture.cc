// authbc-capture.cc — ns-3's receiver rule for two overlapping frames, measured at the PHY
// (work package D of docs/prompts/NEXT_PHASE_PROMPT.md, 2026-11-20).
//
// WHY IT EXISTS. The capture closed forms of (G22)–(G24) assume a receiver that decodes the
// stronger frame when it is θ above the other. ns-3's receiver is code, not that assumption:
//   * a 4 µs preamble-detection window in which the strongest preamble is kept if its SINR is
//     at least 4 dB (PhyEntity::EndPreambleDetectionPeriod; ThresholdPreambleDetectionModel);
//   * after it, a locked frame that a later one can displace only through a frame-capture model
//     (SimpleFrameCaptureModel: 5 dB margin, 16 µs window);
//   * the payload decoded at its SINR by the error-rate model (OFDM: table-based; DSSS: the
//     fallback DsssErrorRateModel).
// This program measures that rule as a curve: two senders, one receiver, a set signal-to-
// interference ratio and a set offset between the two frames' starts.
//
// HOW. Three nodes share one YansWifiChannel. Received powers are set exactly by a
// MatrixPropagationLossModel. The two senders cannot hear each other (300 dB between them), so
// neither defers. Frames are handed straight to each sender's PHY (WifiPhy::Send) at the
// scheduled instants: the MAC and its backoff are not involved, so the offset is exact. The
// receiver's own PHY is the code under test.
//
//   frame Y: the reference, received at --pyDbm (default −60 dBm), sent first;
//   frame X: received at pyDbm + SIR, sent --offsetUs after Y;
//   SIR = P_X − P_Y in dB, swept over --sirList. Each (SIR) block runs --trials trials.
//
// OUTPUT. <out>.csv: one row per SIR: trials, X received, Y received, X/Y ending in RxError.
//         <out>_drops.csv: PhyRxDrop reasons per SIR and frame.
// Every frame is identified by its packet UID, which the PHY preserves.
#include "ns3/core-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/propagation-module.h"
#include "ns3/wifi-module.h"

#include <fstream>
#include <map>
#include <sstream>
#include <vector>

using namespace ns3;

namespace
{
struct Tally
{
    uint64_t xOk = 0, yOk = 0, xErr = 0, yErr = 0;
};

std::map<uint64_t, char> g_whichFrame;          // packet UID -> 'X' or 'Y'
std::map<uint64_t, uint32_t> g_blockOf;          // packet UID -> SIR block
std::vector<Tally> g_tally;
std::map<std::tuple<uint32_t, char, std::string>, uint64_t> g_drops;

void
RxOk(Ptr<const Packet> p, double, WifiMode, WifiPreamble)
{
    auto w = g_whichFrame.find(p->GetUid());
    if (w == g_whichFrame.end()) return;
    Tally& t = g_tally[g_blockOf[p->GetUid()]];
    (w->second == 'X' ? t.xOk : t.yOk)++;
}

void
RxError(Ptr<const Packet> p, double)
{
    auto w = g_whichFrame.find(p->GetUid());
    if (w == g_whichFrame.end()) return;
    Tally& t = g_tally[g_blockOf[p->GetUid()]];
    (w->second == 'X' ? t.xErr : t.yErr)++;
}

void
RxDrop(Ptr<const Packet> p, WifiPhyRxfailureReason reason)
{
    if (!p) return;
    auto w = g_whichFrame.find(p->GetUid());
    if (w == g_whichFrame.end()) return;
    std::ostringstream name;
    name << reason;
    ++g_drops[{g_blockOf[p->GetUid()], w->second, name.str()}];
}

void
SendFrame(Ptr<WifiPhy> phy, Mac48Address from, uint32_t bytes, WifiTxVector tv, char which,
          uint32_t block)
{
    Ptr<Packet> pkt = Create<Packet>(bytes);
    g_whichFrame[pkt->GetUid()] = which;
    g_blockOf[pkt->GetUid()] = block;
    WifiMacHeader hdr(WIFI_MAC_DATA);
    hdr.SetAddr1(Mac48Address::GetBroadcast());
    hdr.SetAddr2(from);
    hdr.SetAddr3(Mac48Address::GetBroadcast());
    hdr.SetDsNotFrom();
    hdr.SetDsNotTo();
    phy->Send(Create<WifiPsdu>(pkt, hdr), tv);
}

void
SetPowers(Ptr<MatrixPropagationLossModel> loss, Ptr<MobilityModel> x, Ptr<MobilityModel> y,
          Ptr<MobilityModel> r, double pyDbm, double sirDb)
{
    // Transmit power is 0 dBm, so a loss of L dB gives −L dBm at the receiver.
    loss->SetLoss(y, r, -pyDbm, true);
    loss->SetLoss(x, r, -(pyDbm + sirDb), true);
}

std::vector<double>
ParseList(const std::string& s)
{
    std::vector<double> v;
    std::stringstream ss(s);
    for (std::string item; std::getline(ss, item, ',');) v.push_back(std::stod(item));
    return v;
}
} // namespace

int
main(int argc, char* argv[])
{
    std::string standard = "80211a";
    bool capture = false;
    double offsetUs = 0.0;
    std::string sirList = "-2,-1,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20";
    uint32_t trials = 2000;
    uint32_t payload = 173;          // the design frame; +8 B LLC as the scenario's frames carry
    double pyDbm = -60.0;
    uint32_t seed = 1;
    std::string outPrefix = "capture";

    CommandLine cmd(__FILE__);
    cmd.AddValue("standard", "80211a (6 Mb/s) or 80211b (1 Mb/s, long preamble)", standard);
    cmd.AddValue("capture", "add SimpleFrameCaptureModel at ns-3's defaults", capture);
    cmd.AddValue("offsetUs", "X starts this many µs after Y (Y first)", offsetUs);
    cmd.AddValue("sirList", "SIR values P_X − P_Y in dB, comma-separated", sirList);
    cmd.AddValue("trials", "trials per SIR value", trials);
    cmd.AddValue("payload", "application payload in bytes (frame = payload + 36 B)", payload);
    cmd.AddValue("pyDbm", "received power of the reference frame Y, dBm", pyDbm);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.Parse(argc, argv);
    NS_ABORT_MSG_IF(standard != "80211a" && standard != "80211b", "standard: 80211a | 80211b");
    NS_ABORT_MSG_IF(offsetUs < 0.0, "offsetUs >= 0: Y is always first");
    const std::vector<double> sirs = ParseList(sirList);
    NS_ABORT_MSG_IF(sirs.empty() || trials == 0, "at least one SIR and one trial");

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    NodeContainer nodes;
    nodes.Create(3);                 // 0 = X, 1 = Y, 2 = receiver
    MobilityHelper mobility;
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(nodes);         // all at the origin: zero propagation delay on every link
    Ptr<MobilityModel> mx = nodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> my = nodes.Get(1)->GetObject<MobilityModel>();
    Ptr<MobilityModel> mr = nodes.Get(2)->GetObject<MobilityModel>();

    Ptr<MatrixPropagationLossModel> loss = CreateObject<MatrixPropagationLossModel>();
    loss->SetDefaultLoss(300.0);     // X and Y never hear each other
    Ptr<YansWifiChannel> channel = CreateObject<YansWifiChannel>();
    channel->SetPropagationLossModel(loss);
    channel->SetPropagationDelayModel(CreateObject<ConstantSpeedPropagationDelayModel>());

    YansWifiPhyHelper phy;
    phy.SetChannel(channel);
    phy.Set("TxPowerStart", DoubleValue(0.0));
    phy.Set("TxPowerEnd", DoubleValue(0.0));
    if (capture) phy.SetFrameCaptureModel("ns3::SimpleFrameCaptureModel");

    WifiHelper wifi;
    const bool dsss = standard == "80211b";
    wifi.SetStandard(dsss ? WIFI_STANDARD_80211b : WIFI_STANDARD_80211a);
    const std::string mode = dsss ? "DsssRate1Mbps" : "OfdmRate6Mbps";
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue(mode),
                                 "ControlMode", StringValue(mode));
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    NetDeviceContainer devs = wifi.Install(phy, mac, nodes);

    auto phyOf = [&](uint32_t i) { return DynamicCast<WifiNetDevice>(devs.Get(i))->GetPhy(); };
    auto macOf = [&](uint32_t i) {
        return Mac48Address::ConvertFrom(devs.Get(i)->GetAddress());
    };
    Ptr<WifiPhy> rx = phyOf(2);
    rx->GetState()->TraceConnectWithoutContext("RxOk", MakeCallback(&RxOk));
    rx->GetState()->TraceConnectWithoutContext("RxError", MakeCallback(&RxError));
    rx->TraceConnectWithoutContext("PhyRxDrop", MakeCallback(&RxDrop));

    // Power levels start at WIFI_MIN_TX_PWR_LEVEL (1) in ns-3.48 (wifi-standard-constants.h:69);
    // with TxPowerStart = TxPowerEnd there is one level, 0 dBm.
    WifiTxVector tv(WifiMode(mode), WIFI_MIN_TX_PWR_LEVEL, WIFI_PREAMBLE_LONG, NanoSeconds(800), 1,
                    1, 0, phyOf(0)->GetChannelWidth(), false);
    const uint32_t bytes = payload + 8;      // + LLC/SNAP; WifiPsdu adds MAC header and FCS
    // A trial lasts two frames, the offset and a wide margin, so the receiver is idle at the
    // start of the next.
    const Time period = dsss ? MilliSeconds(20) : MilliSeconds(5);

    g_tally.assign(sirs.size(), {});
    Time t = Seconds(1.0);
    for (uint32_t b = 0; b < sirs.size(); ++b)
    {
        Simulator::Schedule(t - period / 2, &SetPowers, loss, mx, my, mr, pyDbm, sirs[b]);
        for (uint32_t k = 0; k < trials; ++k, t += period)
        {
            Simulator::Schedule(t, &SendFrame, phyOf(1), macOf(1), bytes, tv, 'Y', b);
            Simulator::Schedule(t + NanoSeconds(static_cast<int64_t>(offsetUs * 1000.0)),
                                &SendFrame, phyOf(0), macOf(0), bytes, tv, 'X', b);
        }
    }
    Simulator::Stop(t + period);
    Simulator::Run();

    std::ofstream out(outPrefix + ".csv");
    out << "standard,capture,offset_us,sir_db,py_dbm,payload,trials,x_ok,y_ok,x_rxerror,"
           "y_rxerror\n";
    for (uint32_t b = 0; b < sirs.size(); ++b)
        out << standard << "," << capture << "," << offsetUs << "," << sirs[b] << "," << pyDbm
            << "," << payload << "," << trials << "," << g_tally[b].xOk << "," << g_tally[b].yOk
            << "," << g_tally[b].xErr << "," << g_tally[b].yErr << "\n";
    std::ofstream drops(outPrefix + "_drops.csv");
    drops << "sir_db,frame,reason,count\n";
    for (const auto& [key, n] : g_drops)
        drops << sirs[std::get<0>(key)] << "," << std::get<1>(key) << "," << std::get<2>(key)
              << "," << n << "\n";
    Simulator::Destroy();
    return 0;
}
