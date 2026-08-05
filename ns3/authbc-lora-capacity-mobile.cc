// authbc-lora-capacity-mobile.cc — the capacity envelope when the UAVs actually fly (E20, M2)
//
// ⚠️ A SEPARATE FILE BY DIRECTION, NOT A MODIFICATION. Mohamed's instruction (2026-07-30, recorded
// in docs/MOBILITY_PLAN.md) is that mobility is added as new scenario files so the frozen static
// results stay bit-reproducible and mobility becomes an ADDITIVE comparison rather than a
// migration. `authbc-lora-capacity.cc` must therefore stay byte-identical; every difference
// between the two files is listed under "WHAT THIS CHANGES vs the static scenario" below.
//
// MODEL CHOICE, and why it is a claim that needs defending. Random Waypoint is what the field
// mostly uses — including a 2025 NS-3 UAV-swarm paper (arXiv 2510.10236) — but it is memoryless
// and has known speed-decay and density artifacts, which is wrong for a swarm holding formation.
// Gauss-Markov gives temporally correlated velocity with a tunable memory alpha, and is one of the
// four models the LoRa-FANET survey (Paredes et al. 2023 §3.2.2) records for FANETs. Full evidence
// and the speed anchor (Davoli et al. 2021: UAVs typically 20-70 km/h = 5.6-19.4 m/s) are in
// docs/MOBILITY_SURVEY.md.
//
// ⚠️ WHAT MOBILITY STILL DOES NOT MODEL, and must be stated wherever this is reported: per-frame
// Doppler fading. At 20 m/s the LoRa coherence time is ~7.3 ms against a 364 ms frame, so the
// channel decorrelates ~50x WITHIN one transmission. This scenario moves nodes between frames; it
// does not fade within them. See MOBILITY_PLAN.md §1a.
//
// ORIGINAL HEADER OF THE STATIC SCENARIO FOLLOWS.
//
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
// E20: the mobility models themselves, plus Box/BoxValue for the Gauss-Markov bounds. The helper
// header alone declares the helper, not the models it can instantiate by type name.
#include "ns3/mobility-module.h"
#include "ns3/box.h"
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

// Mobility (E20). speedMps = 0 reproduces the static scenario exactly and is the control arm:
// if the 0 m/s run does not match `authbc-lora-capacity.cc`, this file is wrong, not the result.
double speedMps = 0.0;              //!< Mean node speed (m/s); 0 = static control
std::string mobilityModel = "gaussmarkov"; //!< "static" | "gaussmarkov" | "rwp"
// Gauss-Markov memory. alpha=1 is straight-line constant velocity, alpha=0 is memoryless
// (Brownian). 0.85 is the commonly used FANET value: strongly correlated, so a UAV does not
// reverse direction between updates, which is the whole reason G-M is preferred to RWP here.
double gmAlpha = 0.85;
double gmTimeStepS = 1.0;           //!< Velocity-update interval (s)

// Base index for the senders' pinned RNG streams (F36). Well above anything ns-3 auto-allocates,
// so pinning cannot collide with a stream the simulator hands out on its own.
constexpr int64_t AUTHBC_SENDER_STREAM_BASE = 1000000;

// ⚠️ Pinning is required for VALID mobility comparison and prevents BIT-IDENTICAL comparison with
// the frozen static scenario — the two properties are mutually exclusive, so both are offered:
//   --pinStreams=false --speed=0  reproduces authbc-lora-capacity.cc exactly (porting correctness)
//   --pinStreams=true  (default)  makes the traffic realisation independent of the mobility model,
//                                 so a static-vs-mobile difference can only come from motion
bool pinStreams = true;

// Channel model
// Channel model (E12). The module's own "realistic" option aggregates correlated shadowing AND
// BuildingPenetrationLoss. **Building penetration is wrong physics for a UAV air-to-air link** —
// drones fly above the buildings, and that model also needs MobilityBuildingInfo installed, which
// this scenario never does. So we expose shadowing on its own rather than the module's bundle:
//   "ideal"     -> LogDistance only. No link loss; all loss is collisions. (previous behaviour)
//   "shadowing" -> LogDistance + CorrelatedShadowing. The honest air-to-air model.
// See F23: hardware measurements of air-to-air LoRa show 9.6 points of loss at 1000 m that the
// idealised model does not produce at all.
std::string channelModel = "ideal";
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


/**
 * \brief A LoRa sender with **one-sided** inter-transmission jitter (audit E13/F26).
 *
 * The module's PeriodicSender fires on an exact interval. Because every device in this scenario
 * shares one period and LoRaWAN ALOHA has no backoff, relative phases are then frozen for the whole
 * run: a pair that collides once collides on every transmission, and a pair that misses never
 * collides. Delivery becomes bimodal — measured at N=5, 22 of 30 seeds give exactly 1.000 and the
 * rest fall to 0.20-0.84 — so a small-sample mean is meaningless against a hard threshold.
 *
 * ⚠️ The jitter is **one-sided by construction** (``[T, T+J]``, never earlier than T). A symmetric
 * ±J would let half the transmissions arrive sooner than the duty-cycle interval, silently
 * violating the 1 % EU868 regulation on which this entire arm's Lambda and batch argument rest.
 * That is the whole reason this class exists rather than a two-line attribute change.
 *
 * Real LoRaWAN Class A devices randomise transmission timing for exactly this reason; the module's
 * sender simply does not model it. Subclassing was not possible: SendPacket() is non-virtual and
 * the interval and event handle are private, so this reimplements the few lines that matter.
 */
class JitteredSender : public Application
{
  public:
    JitteredSender(Time interval, Time jitter, uint32_t pktSize)
        : m_interval(interval), m_jitter(jitter), m_pktSize(pktSize)
    {
        m_rand = CreateObject<UniformRandomVariable>();
        m_rand->SetAttribute("Min", DoubleValue(0.0));
        m_rand->SetAttribute("Max", DoubleValue(jitter.GetSeconds()));
    }

    /** Next fire time: the duty-cycle interval plus a non-negative random extra. */
    Time NextDelay() const
    {
        return m_interval + Seconds(m_rand->GetValue());
    }

    /** Pin this sender's RNG streams so they do not depend on object-creation order.
     *
     * ⚠️ This is the fix for the confound recorded in F36. ns-3 hands each newly created
     * RandomVariableStream the next index from a global counter, and the mobility models are
     * created BEFORE the senders — so installing Gauss-Markov instead of ConstantPosition shifts
     * every sender's stream. Under the ALOHA matrix that alone moved delivery 0.7709 -> 0.7209,
     * which reads exactly like a 5-point mobility penalty and is nothing of the kind.
     *
     * Pinning by node id makes the traffic realisation identical across mobility configurations,
     * so a static-vs-mobile difference can only come from motion.
     */
    void PinStreams(int64_t base)
    {
        m_pinned = true;
        m_streamBase = base;
        m_rand->SetStream(base);
    }

  private:
    void StartApplication() override
    {
        if (!m_mac)
        {
            auto dev = DynamicCast<LoraNetDevice>(GetNode()->GetDevice(0));
            NS_ABORT_MSG_IF(!dev, "JitteredSender expects a LoraNetDevice on device 0");
            m_mac = dev->GetMac();
        }
        // Randomise the first transmission over a full interval, as PeriodicSender does.
        Ptr<UniformRandomVariable> first = CreateObject<UniformRandomVariable>();
        // Pinned for the same reason as m_rand: the start offsets set the relative phases of every
        // node, so if they shift with mobility configuration the collision pattern changes for
        // reasons that have nothing to do with movement.
        //
        // ⚠️ MUST stay conditional. Setting this unconditionally gave every node the SAME stream
        // (m_streamBase defaults to 0 when unpinned), so all nodes drew the same start offset and
        // transmitted in lockstep — delivery collapsed to 0.0298. Caught by the property-1 check.
        if (m_pinned)
        {
            first->SetStream(m_streamBase + 1);
        }
        m_event = Simulator::Schedule(Seconds(first->GetValue(0.0, m_interval.GetSeconds())),
                                      &JitteredSender::Fire, this);
    }

    void StopApplication() override { Simulator::Cancel(m_event); }

    void Fire()
    {
        m_mac->Send(Create<Packet>(m_pktSize));
        m_event = Simulator::Schedule(NextDelay(), &JitteredSender::Fire, this);
    }

    Time m_interval;
    Time m_jitter;
    uint32_t m_pktSize;
    bool m_pinned = false;
    int64_t m_streamBase = 0;
    Ptr<UniformRandomVariable> m_rand;
    Ptr<LorawanMac> m_mac;
    EventId m_event;
};

int
main(int argc, char* argv[])
{
    std::string interferenceMatrix = "aloha";
    uint32_t dataRate = 5;        // 0=SF12 .. 5=SF7
    // ⚠️ Must not exceed the module's enforced RP002 Table 12 limit for the chosen DR (222 B at
    // DR5). A larger value is silently rejected by the MAC and the run sends NOTHING — which used
    // to surface only as the "no packets were sent" abort below. 218 B is the AUTHBC frame at
    // b=6, which is what run_lora_capacity.py computes and what the frozen results use.
    uint32_t payloadBytes = 218;  // AUTHBC frame at DR5, b=6: H_f 44 + g_a 64 + chain 32 + 6*13
    double appPeriodS = 38.4;     // 1 % duty cycle on that frame's time on air
    uint32_t seed = 1;
    std::string outPrefix = "authbc_lora_cap";
    // Gateway provisioning. F19: the two presets differ by more than their names suggest, and the
    // difference dominates the capacity result:
    //   "aloha" -> 1 logical channel (868.1), 1 demodulation path  [models an AD HOC PEER]
    //   "eu"    -> 3 logical channels,        8 demodulation paths [models a GATEWAY]
    // Both still force a single SF (see drDistribution below), so neither buys SF orthogonality.
    //
    // ⚠️ F21: "aloha" is the RIGHT preset for this thesis, not merely the harshest. Our system is a
    // decentralised FANET, and a UAV peer has ONE radio and ONE demodulator; 8 paths across 3
    // channels models a ground gateway, which is a different question. Note also that a peer
    // listening on 868.1 cannot hear a frame sent on 868.3 — for broadcast, where every node must
    // receive every record, all nodes must share one channel (docs/TRADEOFFS.md §1a).
    //
    // ⚠️ E11: the "aloha" preset sets the g1 sub-band duty cycle to 1 (i.e. 100%), so the MAC does
    // NOT enforce the regulatory 1 %. That limit is imposed here by appPeriodS instead. Changing
    // appPeriod without changing the preset silently breaks the regulation this whole arm rests on.
    std::string gwRegion = "aloha";
    // Crystal tolerance, ppm (audit F26). Default 0 preserves the frozen configuration exactly.
    //
    // ⚠️ Why this exists: every device shares ONE exact period, so relative phases are frozen for
    // the whole run — a pair that collides on its first transmission collides on every one, and a
    // pair that misses never collides. Delivery is therefore bimodal and hugely seed-dependent
    // (measured at N=5: 22/30 seeds give exactly 1.000, the rest 0.20-0.84). Real SX127x crystals
    // are +/-20 ppm, which over a 3600 s run is +/-72 ms of drift against a 364 ms frame — enough
    // for collisions to migrate rather than persist. The 802.11 arm already de-synchronises its
    // sources for exactly this reason; this is the LoRa equivalent.
    double clockPpm = 0.0;
    // One-sided inter-transmission jitter, seconds (E13). 0 = the frozen exact-period behaviour.
    // Only ever DELAYS a transmission, so the 1 % duty cycle is preserved. See JitteredSender.
    double txJitterS = 0.0;

    CommandLine cmd(__FILE__);
    cmd.AddValue("nDevices", "Number of end devices to include in the simulation", nDevices);
    cmd.AddValue("simulationTime", "Simulation Time (s)", simulationTimeSeconds);
    cmd.AddValue("interferenceMatrix",
                 "Interference matrix to use [aloha, goursaud]",
                 interferenceMatrix);
    cmd.AddValue("radius", "Radius (m) of the deployment", radiusMeters);
    cmd.AddValue("speed", "mean node speed (m/s); 0 = static control arm", speedMps);
    cmd.AddValue("mobilityModel", "static | gaussmarkov | rwp", mobilityModel);
    cmd.AddValue("gmAlpha", "Gauss-Markov memory alpha in [0,1]", gmAlpha);
    cmd.AddValue("gmTimeStep", "Gauss-Markov velocity update interval (s)", gmTimeStepS);
    cmd.AddValue("pinStreams",
                 "pin sender RNG streams so traffic is identical across mobility models (F36); "
                 "false reproduces the frozen static scenario bit-identically at speed 0",
                 pinStreams);
    cmd.AddValue("dataRate", "LoRaWAN DR 0..5 (0=SF12 .. 5=SF7), forced on every device", dataRate);
    cmd.AddValue("payloadBytes", "application payload = the AUTHBC frame size", payloadBytes);
    cmd.AddValue("appPeriod", "seconds between transmissions (the duty-cycle interval)", appPeriodS);
    cmd.AddValue("seed", "RNG run number", seed);
    cmd.AddValue("outPrefix", "output file prefix", outPrefix);
    cmd.AddValue("txJitter",
                 "one-sided inter-transmission jitter in seconds (0 = exact period, the default)",
                 txJitterS);
    cmd.AddValue("clockPpm",
                 "per-device crystal tolerance in ppm (0 = frozen phases, the original behaviour)",
                 clockPpm);
    cmd.AddValue("channelModel",
                 "propagation [ideal = LogDistance only, shadowing = + correlated shadowing]",
                 channelModel);
    cmd.AddValue("gwRegion",
                 "gateway provisioning [aloha = 1 channel/1 demod path, eu = 3 channels/8 paths]",
                 gwRegion);
    cmd.Parse(argc, argv);

    NS_ABORT_MSG_IF(dataRate > 5, "DR must be 0..5 (LoRa modulation only)");
    // Fail early and legibly rather than as a mystifying zero-send run 3600 simulated seconds
    // later. RP002 Table 12 (repeater-compatible) is what this module enforces.
    const uint32_t kRp002Table12MaxPayload[6] = {51, 51, 51, 115, 222, 222};  // DR0..DR5
    NS_ABORT_MSG_IF(payloadBytes > kRp002Table12MaxPayload[dataRate],
                    "payloadBytes " << payloadBytes << " exceeds the module's RP002 Table 12 limit "
                    << kRp002Table12MaxPayload[dataRate] << " B for DR" << dataRate
                    << " — the MAC will reject every packet and nothing will be sent");
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
    // E20. The bounding box is the deployment disc extruded in z. Gauss-Markov REFLECTS off the
    // box, so nodes stay in the region the propagation model was characterised for instead of
    // drifting to arbitrary range — a node at 20 m/s covers 72 km in a 3600 s run, which no fixed
    // disc could contain (MOBILITY_PLAN.md §1b).
    const double zLo = 1.2;    // the static scenario's device altitude, kept as the floor
    const double zHi = 120.0;  // typical small-UAV ceiling; z is bounded, not free
    NS_ABORT_MSG_IF(speedMps < 0.0, "speed must be >= 0");
    NS_ABORT_MSG_IF(gmAlpha < 0.0 || gmAlpha > 1.0, "gmAlpha must be in [0,1]");

    if (mobilityModel == "static" || speedMps == 0.0)
    {
        // The control arm. Identical to authbc-lora-capacity.cc, so a 0 m/s run of THIS file must
        // reproduce that scenario; any difference is a bug in this file, not a mobility finding.
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    }
    else if (mobilityModel == "gaussmarkov")
    {
        mobility.SetMobilityModel(
            "ns3::GaussMarkovMobilityModel",
            "Bounds", BoxValue(Box(-radiusMeters, radiusMeters, -radiusMeters, radiusMeters,
                                   zLo, zHi)),
            "TimeStep", TimeValue(Seconds(gmTimeStepS)),
            "Alpha", DoubleValue(gmAlpha),
            "MeanVelocity",
            StringValue("ns3::UniformRandomVariable[Min=" + std::to_string(speedMps * 0.5) +
                        "|Max=" + std::to_string(speedMps * 1.5) + "]"),
            // Level flight on average: mean pitch 0 means no systematic climb or descent, and the
            // small normal spread lets altitude vary without the swarm drifting into the ceiling.
            "MeanPitch", StringValue("ns3::UniformRandomVariable[Min=-0.05|Max=0.05]"),
            "MeanDirection",
            StringValue("ns3::UniformRandomVariable[Min=0|Max=6.283185307]"),
            "NormalVelocity",
            StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.5|Bound=1.0]"),
            "NormalDirection",
            StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.2|Bound=0.4]"),
            "NormalPitch",
            StringValue("ns3::NormalRandomVariable[Mean=0|Variance=0.02|Bound=0.04]"));
    }
    else if (mobilityModel == "rwp")
    {
        // The field's default, run as a BASELINE so the Gauss-Markov choice is a measured
        // comparison rather than an assertion (docs/MOBILITY_SURVEY.md §2a).
        mobility.SetMobilityModel(
            "ns3::RandomWaypointMobilityModel",
            "Speed", StringValue("ns3::UniformRandomVariable[Min=" +
                                 std::to_string(speedMps * 0.5) + "|Max=" +
                                 std::to_string(speedMps * 1.5) + "]"),
            "Pause", StringValue("ns3::ConstantRandomVariable[Constant=0.0]"),
            "PositionAllocator",
            StringValue("ns3::UniformDiscPositionAllocator[rho=" +
                        std::to_string(radiusMeters) + "|X=0.0|Y=0.0]"));
    }
    else
    {
        NS_ABORT_MSG("mobilityModel must be static | gaussmarkov | rwp");
    }

    /************************
     *  Create the channel  *
     ************************/

    // Create the lora channel object
    Ptr<LogDistancePropagationLossModel> loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetPathLossExponent(3.76);
    loss->SetReference(1, 7.7);

    NS_ABORT_MSG_IF(channelModel != "ideal" && channelModel != "shadowing",
                    "channelModel must be 'ideal' or 'shadowing'");
    if (channelModel == "shadowing")
    {
        // Correlated shadowing ONLY. Deliberately no BuildingPenetrationLoss: see the note at the
        // declaration — UAVs are not indoors, and the building model would need MobilityBuildingInfo
        // that this scenario does not install.
        Ptr<CorrelatedShadowingPropagationLossModel> shadowing =
            CreateObject<CorrelatedShadowingPropagationLossModel>();
        loss->SetNext(shadowing);
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
    NS_ABORT_MSG_IF(gwRegion != "aloha" && gwRegion != "eu", "gwRegion must be 'aloha' or 'eu'");
    macHelper.SetRegion(gwRegion == "eu" ? LorawanMacHelper::EU : LorawanMacHelper::ALOHA);

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
    // ⚠️ Reset the model before installing. The helper still carries the END DEVICES' mobility
    // model, so without this the gateway would fly too — silently changing what is being measured
    // from "mobile swarm, fixed receiver" to "everything moves".
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
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
    ApplicationContainer appContainer;
    if (txJitterS > 0.0)
    {
        for (auto nd = endDevices.Begin(); nd != endDevices.End(); ++nd)
        {
            auto app = CreateObject<JitteredSender>(Seconds(appPeriodSeconds), Seconds(txJitterS),
                                                    static_cast<uint32_t>(packetSize));
            // Two pinned streams per node (jitter + start offset), keyed on node id so the traffic
            // realisation is identical whatever mobility model is installed. The base is far above
            // the auto-allocated range so it cannot alias a stream ns-3 hands out itself.
            if (pinStreams)
            {
                app->PinStreams(AUTHBC_SENDER_STREAM_BASE +
                                2 * static_cast<int64_t>((*nd)->GetId()));
            }
            (*nd)->AddApplication(app);
            appContainer.Add(app);
        }
    }
    else
    {
        PeriodicSenderHelper appHelper = PeriodicSenderHelper();
        appHelper.SetPeriod(Seconds(appPeriodSeconds));
        appHelper.SetPacketSize(packetSize);
        appContainer = appHelper.Install(endDevices);
    }

    // Give each device its own slightly-off period so phases drift instead of staying frozen.
    if (clockPpm > 0.0)
    {
        Ptr<UniformRandomVariable> ppm = CreateObject<UniformRandomVariable>();
        ppm->SetAttribute("Min", DoubleValue(-clockPpm));
        ppm->SetAttribute("Max", DoubleValue(clockPpm));
        for (uint32_t i = 0; i < appContainer.GetN(); ++i)
        {
            auto sender = DynamicCast<PeriodicSender>(appContainer.Get(i));
            NS_ABORT_MSG_IF(!sender, "expected a PeriodicSender application");
            sender->SetInterval(Seconds(appPeriodSeconds * (1.0 + ppm->GetValue() * 1e-6)));
        }
    }

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

    // ⚠️ Displacement diagnostic, and it is not optional. A first smoke test showed speed=5 and
    // speed=20 producing byte-identical delivery, which has two very different explanations:
    // either the nodes fly and the link margin swamps the effect (the predicted outcome), or the
    // mobility model never moved them and the whole difference from the static arm is RNG stream
    // displacement. Delivery alone cannot tell those apart, so the scenario measures the motion
    // itself and reports it beside the result.
    std::vector<Vector> startPos;
    startPos.reserve(endDevices.GetN());
    for (auto j = endDevices.Begin(); j != endDevices.End(); ++j)
    {
        startPos.push_back((*j)->GetObject<MobilityModel>()->GetPosition());
    }

    NS_LOG_INFO("Running simulation...");
    Simulator::Run();

    double sumDisp = 0.0;
    double maxDisp = 0.0;
    {
        std::size_t i = 0;
        for (auto j = endDevices.Begin(); j != endDevices.End(); ++j, ++i)
        {
            const Vector p = (*j)->GetObject<MobilityModel>()->GetPosition();
            const double d = CalculateDistance(p, startPos[i]);
            sumDisp += d;
            maxDisp = std::max(maxDisp, d);
        }
    }
    const double meanDisp = endDevices.GetN() ? sumDisp / endDevices.GetN() : 0.0;

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
        << "gw_region," << gwRegion << "\n"
        << "channel_model," << channelModel << "\n"
        << "clock_ppm," << clockPpm << "\n"
        << "tx_jitter_s," << txJitterS << "\n"
        << "radius_m," << radiusMeters << "\n"
        << "mobility_model," << (speedMps == 0.0 ? "static" : mobilityModel) << "\n"
        << "speed_mps," << speedMps << "\n"
        << "gm_alpha," << gmAlpha << "\n"
        << "gm_time_step_s," << gmTimeStepS << "\n"
        << "pin_streams," << (pinStreams ? 1 : 0) << "\n"
        << "mean_displacement_m," << meanDisp << "\n"
        << "max_displacement_m," << maxDisp << "\n"
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
