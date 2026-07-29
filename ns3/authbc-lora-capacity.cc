// authbc-lora-capacity.cc — how many UAVs can share one LoRa channel? (item D2, docs/02 §9)
//
// DERIVED FROM contrib/lorawan/examples/aloha-throughput.cc (Magrin et al.), changed only where
// this study needs something different. A from-scratch rewrite configured every component
// correctly — right device count, right data rate, live PHY — and still transmitted nothing, so
// this starts from a file known to work in this build. Provenance matters more than authorship.
//
// WHY IT EXISTS. The LoRa arm is otherwise analytical: time on air comes from the SX1276 formula
// and the sustainable rate from the EU868 duty cycle, both deterministic, so simulating them would
// be circular. Exactly one quantity is not derivable that way, and it is the one the 802.11 arm
// already reports: the MULTI-NODE capacity envelope. LoRaWAN uplinks are pure ALOHA, so N devices
// collide and the delivered fraction falls with N. This measures that, turning OPEN_ITEMS D2 ("no
// measurement of any kind") into a simulated bound.
//
// WHAT THIS CHANGES vs the original example:
//   * the data rate is FORCED (a design variable here, docs/02 §9a — an input, not an ADR outcome)
//   * the payload is the AUTHBC frame H_f + g_a + b*s, so collisions reflect real airtime
//   * the transmission period is the duty-cycle interval, not the simulation length
//   * results go to a CSV keyed for ns3/run_lora_capacity.py
//
#include "ns3/core-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/log.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE("AlohaThroughput");

// Network settings
int nDevices = 200;                 //!< Number of end device nodes to create
int nGateways = 1;                  //!< Number of gateway nodes to create
double radiusMeters = 1000;         //!< Radius (m) of the deployment
double simulationTimeSeconds = 100; //!< Scenario duration (s) in simulated time

// Channel model
bool realisticChannelModel = false; //!< Whether to use a more realistic channel model with
                                    //!< buildings and correlated shadowing

/** Record received pkts by Data Rate (DR) [index 0 -> DR5, index 5 -> DR0]. */
auto packetsSent = std::vector<int>(6, 0);
/** Record received pkts by Data Rate (DR) [index 0 -> DR5, index 5 -> DR0]. */
auto packetsReceived = std::vector<int>(6, 0);

/**
 * Record the beginning of a transmission by an end device.
 *
 * @param packet A pointer to the packet sent.
 * @param senderNodeId Node id of the sender end device.
 */
void
OnTransmissionCallback(Ptr<const Packet> packet, uint32_t senderNodeId)
{
    NS_LOG_FUNCTION(packet << senderNodeId);
    LoraTag tag;
    packet->PeekPacketTag(tag);
    packetsSent.at(tag.GetSpreadingFactor() - 7)++;
}

/**
 * Record the correct reception of a packet by a gateway.
 *
 * @param packet A pointer to the packet received.
 * @param receiverNodeId Node id of the receiver gateway.
 */
void
OnPacketReceptionCallback(Ptr<const Packet> packet, uint32_t receiverNodeId)
{
    NS_LOG_FUNCTION(packet << receiverNodeId);
    LoraTag tag;
    packet->PeekPacketTag(tag);
    packetsReceived.at(tag.GetSpreadingFactor() - 7)++;
}

int
main(int argc, char* argv[])
{
    std::string interferenceMatrix = "aloha";
    uint32_t dataRate = 5;        // 0=SF12 .. 5=SF7
    uint32_t payloadBytes = 231;  // AUTHBC frame at DR5: H_f 44 + g_a 64 + chain 32 + 7*13
    double appPeriodS = 38.4;     // 1 % duty cycle on that frame's time on air
    uint32_t seed = 1;
    std::string outPrefix = "authbc_lora_cap";

    CommandLine cmd(__FILE__);
    cmd.AddValue("nDevices", "Number of end devices to include in the simulation", nDevices);
    cmd.AddValue("simulationTime", "Simulation Time (s)", simulationTimeSeconds);
    cmd.AddValue("interferenceMatrix",
                 "Interference matrix to use [aloha, goursaud]",
                 interferenceMatrix);
    cmd.AddValue("radius", "Radius (m) of the deployment", radiusMeters);
    cmd.AddValue("dataRate", "LoRaWAN DR 0..5 (0=SF12 .. 5=SF7), forced on every device", dataRate);
    cmd.AddValue("payloadBytes", "application payload = the AUTHBC frame size", payloadBytes);
    cmd.AddValue("appPeriod", "seconds between transmissions (the duty-cycle interval)", appPeriodS);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.Parse(argc, argv);

    NS_ABORT_MSG_IF(dataRate > 5, "DR must be 0..5 (LoRa modulation only)");
    NS_ABORT_MSG_IF(payloadBytes > 255, "payload exceeds the LoRa PHY limit");
    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(seed);

    double appPeriodSeconds = appPeriodS;

    // Set up logging
    LogComponentEnable("AlohaThroughput", LOG_LEVEL_ALL);

    // Make all devices use SF7 (i.e., DR5)
    // Config::SetDefault ("ns3::EndDeviceLorawanMac::DataRate", UintegerValue (5));

    if (interferenceMatrix == "aloha")
    {
        LoraInterferenceHelper::collisionMatrix = LoraInterferenceHelper::ALOHA;
    }
    else if (interferenceMatrix == "goursaud")
    {
        LoraInterferenceHelper::collisionMatrix = LoraInterferenceHelper::GOURSAUD;
    }

    /***********
     *  Setup  *
     ***********/

    // Mobility
    MobilityHelper mobility;
    mobility.SetPositionAllocator("ns3::UniformDiscPositionAllocator",
                                  "rho",
                                  DoubleValue(radiusMeters),
                                  "X",
                                  DoubleValue(0.0),
                                  "Y",
                                  DoubleValue(0.0));
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");

    /************************
     *  Create the channel  *
     ************************/

    // Create the lora channel object
    Ptr<LogDistancePropagationLossModel> loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetPathLossExponent(3.76);
    loss->SetReference(1, 7.7);

    if (realisticChannelModel)
    {
        // Create the correlated shadowing component
        Ptr<CorrelatedShadowingPropagationLossModel> shadowing =
            CreateObject<CorrelatedShadowingPropagationLossModel>();

        // Aggregate shadowing to the logdistance loss
        loss->SetNext(shadowing);

        // Add the effect to the channel propagation loss
        Ptr<BuildingPenetrationLoss> buildingLoss = CreateObject<BuildingPenetrationLoss>();

        shadowing->SetNext(buildingLoss);
    }

    Ptr<PropagationDelayModel> delay = CreateObject<ConstantSpeedPropagationDelayModel>();

    Ptr<LoraChannel> channel = CreateObject<LoraChannel>(loss, delay);

    /************************
     *  Create the helpers  *
     ************************/

    // Create the LoraPhyHelper
    LoraPhyHelper phyHelper = LoraPhyHelper();
    phyHelper.SetChannel(channel);

    // Create the LorawanMacHelper
    LorawanMacHelper macHelper = LorawanMacHelper();
    macHelper.SetRegion(LorawanMacHelper::ALOHA);

    // Create the LoraHelper
    LoraHelper helper = LoraHelper();
    helper.EnablePacketTracking(); // Output filename

    // Create the NetworkServerHelper
    NetworkServerHelper nsHelper = NetworkServerHelper();

    // Create the ForwarderHelper
    ForwarderHelper forHelper = ForwarderHelper();

    /************************
     *  Create End Devices  *
     ************************/

    // Create a set of nodes
    NodeContainer endDevices;
    endDevices.Create(nDevices);

    // Assign a mobility model to each node
    mobility.Install(endDevices);

    // Make it so that nodes are at a certain height > 0
    for (auto j = endDevices.Begin(); j != endDevices.End(); ++j)
    {
        Ptr<MobilityModel> mobility = (*j)->GetObject<MobilityModel>();
        Vector position = mobility->GetPosition();
        position.z = 1.2;
        mobility->SetPosition(position);
    }

    // Create the LoraNetDevices of the end devices
    uint8_t nwkId = 54;
    uint32_t nwkAddr = 1864;
    Ptr<LoraDeviceAddressGenerator> addrGen =
        CreateObject<LoraDeviceAddressGenerator>(nwkId, nwkAddr);

    // Create the LoraNetDevices of the end devices
    macHelper.SetAddressGenerator(addrGen);
    phyHelper.SetDeviceType(LoraPhyHelper::ED);
    macHelper.SetDeviceType(LorawanMacHelper::ED_A);
    helper.Install(phyHelper, macHelper, endDevices);

    // Now end devices are connected to the channel

    // Connect trace sources
    for (auto j = endDevices.Begin(); j != endDevices.End(); ++j)
    {
        Ptr<Node> node = *j;
        Ptr<LoraNetDevice> loraNetDevice = DynamicCast<LoraNetDevice>(node->GetDevice(0));
        Ptr<LoraPhy> phy = loraNetDevice->GetPhy();
    }

    /*********************
     *  Create Gateways  *
     *********************/

    // Create the gateway nodes (allocate them uniformly on the disc)
    NodeContainer gateways;
    gateways.Create(nGateways);

    Ptr<ListPositionAllocator> allocator = CreateObject<ListPositionAllocator>();
    // Make it so that nodes are at a certain height > 0
    allocator->Add(Vector(0.0, 0.0, 15.0));
    mobility.SetPositionAllocator(allocator);
    mobility.Install(gateways);

    // Create a netdevice for each gateway
    phyHelper.SetDeviceType(LoraPhyHelper::GW);
    macHelper.SetDeviceType(LorawanMacHelper::GW);
    helper.Install(phyHelper, macHelper, gateways);

    NS_LOG_DEBUG("Completed configuration");

    /*********************************************
     *  Install applications on the end devices  *
     *********************************************/

    Time appStopTime = Seconds(simulationTimeSeconds);
    int packetSize = static_cast<int>(payloadBytes);
    PeriodicSenderHelper appHelper = PeriodicSenderHelper();
    appHelper.SetPeriod(Seconds(appPeriodSeconds));
    appHelper.SetPacketSize(packetSize);
    ApplicationContainer appContainer = appHelper.Install(endDevices);

    appContainer.Start(Time(0));
    appContainer.Stop(appStopTime);

    std::ofstream outputFile;
    // Delete contents of the file as it is opened
    outputFile.open("durations.txt", std::ofstream::out | std::ofstream::trunc);
    for (uint8_t sf = 7; sf <= 12; sf++)
    {
        LoraTxParameters txParams;
        txParams.spreadingFactor = sf;
        txParams.bandwidthHz = 125'000;
        txParams.codingRate = CodingRate::CR_4_5;
        txParams.lowDataRateOptimize = (sf == 11 || sf == 12);
        txParams.preambleLenSymb = 8;
        txParams.implicitHeader = false;
        txParams.crcEnabled = true;

        Ptr<Packet> pkt = Create<Packet>(packetSize);

        LoraFrameHeader frameHdr = LoraFrameHeader();
        frameHdr.SetAsUplink();
        frameHdr.SetFPort(1);
        frameHdr.SetAddress(LoraDeviceAddress());
        frameHdr.SetAdr(false);
        frameHdr.SetAdrAckReq(false);
        frameHdr.SetFCnt(0);
        pkt->AddHeader(frameHdr);

        LorawanMacHeader macHdr = LorawanMacHeader();
        macHdr.SetFType(LorawanMacHeader::UNCONFIRMED_DATA_UP);
        macHdr.SetMajor(1);
        pkt->AddHeader(macHdr);

        outputFile << LoraPhy::GetTimeOnAir(pkt->GetSize(), txParams).GetMicroSeconds() << " ";
    }
    outputFile.close();

    /**************************
     *  Create network server  *
     ***************************/

    // Create the network server node
    Ptr<Node> networkServer = CreateObject<Node>();

    // PointToPoint links between gateways and server
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));
    // Store network server app registration details for later
    P2PGwRegistration_t gwRegistration;
    for (auto gw = gateways.Begin(); gw != gateways.End(); ++gw)
    {
        auto container = p2p.Install(networkServer, *gw);
        auto serverP2PNetDev = DynamicCast<PointToPointNetDevice>(container.Get(0));
        gwRegistration.emplace_back(serverP2PNetDev, *gw);
    }

    // Create a network server for the network
    nsHelper.SetGatewaysP2P(gwRegistration);
    nsHelper.SetEndDevices(endDevices);
    nsHelper.Install(networkServer);

    // Create a forwarder for each gateway
    forHelper.Install(gateways);

    // Install trace sources
    for (auto node = gateways.Begin(); node != gateways.End(); node++)
    {
        DynamicCast<LoraNetDevice>((*node)->GetDevice(0))
            ->GetPhy()
            ->TraceConnectWithoutContext("ReceivedPacket", MakeCallback(OnPacketReceptionCallback));
    }

    // Install trace sources
    for (auto node = endDevices.Begin(); node != endDevices.End(); node++)
    {
        DynamicCast<LoraNetDevice>((*node)->GetDevice(0))
            ->GetPhy()
            ->TraceConnectWithoutContext("StartSending", MakeCallback(OnTransmissionCallback));
    }

    // Forced DR: distribution index 0 maps to DR5, 1 to DR4, ..., so put the whole mass at
    // (5 - dataRate). This is the module's supported way to impose a DR while leaving the rest of
    // the MAC state consistent.
    std::vector<double> drDistribution(6, 0.0);
    drDistribution.at(5 - dataRate) = 1.0;
    LorawanMacHelper::SetSpreadingFactorsGivenDistribution(endDevices, gateways, drDistribution);

    ////////////////
    // Simulation //
    ////////////////

    Simulator::Stop(appStopTime + Hours(1));

    NS_LOG_INFO("Running simulation...");
    Simulator::Run();

    Simulator::Destroy();

    /////////////////////////////
    // Print results to stdout //
    /////////////////////////////
    NS_LOG_INFO("Computing performance metrics...");

    long sent = 0;
    long received = 0;
    for (int i = 0; i < 6; i++)
    {
        sent += packetsSent.at(i);
        received += packetsReceived.at(i);
        std::cout << packetsSent.at(i) << " " << packetsReceived.at(i) << std::endl;
    }

    // A run that sent nothing is a broken run, not a capacity result of zero. Fail loudly rather
    // than emit a delivered fraction that would read as a finding (Law 3).
    NS_ABORT_MSG_IF(sent == 0, "no packets were sent — the scenario is misconfigured");

    std::ofstream out(outPrefix + ".csv");
    out << "key,value\n"
        << "n_devices," << nDevices << "\n"
        << "data_rate," << dataRate << "\n"
        << "payload_bytes," << payloadBytes << "\n"
        << "app_period_s," << appPeriodSeconds << "\n"
        << "sim_time_s," << simulationTimeSeconds << "\n"
        << "seed," << seed << "\n"
        << "sent," << sent << "\n"
        << "received," << received << "\n"
        << "delivered_frac," << (static_cast<double>(received) / sent) << "\n";
    out.close();
    return 0;
}
