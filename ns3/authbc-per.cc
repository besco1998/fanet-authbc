// authbc-per.cc — the frame loss to noise, PER(ℓ), that ns-3's own error-rate model gives a
// non-HT OFDM frame received alone at a fixed power. Task of 2026-11-17, C5 respecified as work
// package D of docs/prompts/CAPTURE_PROMPT.md (§8.3 step 1). Nothing is simulated: the program
// calls the model the scenario installs (TableBasedErrorRateModel, yans-wifi-helper.cc:76) with
// the inputs the PHY gives it for a frame without interference:
//   * SNR = P_rx / (F · k · 290 K · B): interference-helper.cc:408–413, k = 1.3803e-23 J/K,
//     F = RxNoiseFigure = 7 dB (wifi-phy.cc:186–197), B = 20 MHz;
//   * the non-HT header: one 4 µs chunk at 6 Mb/s, nbits = rate · duration
//     (interference-helper.cc:520–535);
//   * the payload: one chunk at the data rate over the whole payload duration, N_sym · 4 µs with
//     N_sym = ceil((16 + 8·L + 6) / N_DBPS), so nbits = N_DBPS · N_sym (interference-helper.cc:
//     538–560);
//   * the frame succeeds only if both chunks do: PER = 1 − csr_header · csr_payload.
// L is the MPDU, the application payload ℓ plus 36 B (LLC 8, MAC header 24, FCS 4).
//
//   ./ns3 run "authbc-per --mode=OfdmRate48Mbps --rxPowerDbm=-77 --sizes=146,173,425"

#include "ns3/core-module.h"
#include "ns3/wifi-module.h"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>

using namespace ns3;

int
main(int argc, char* argv[])
{
    std::string modeName = "OfdmRate48Mbps";
    double rxPowerDbm = -77.0;
    std::string sizes = "146,173,425";
    CommandLine cmd(__FILE__);
    cmd.AddValue("mode", "non-HT OFDM data mode, e.g. OfdmRate48Mbps", modeName);
    cmd.AddValue("rxPowerDbm", "received power of the frame, dBm", rxPowerDbm);
    cmd.AddValue("sizes", "application payloads in bytes, comma-separated", sizes);
    cmd.Parse(argc, argv);

    const WifiMode data = WifiMode(modeName);
    const WifiMode header = OfdmPhy::GetOfdmRate6Mbps();
    WifiTxVector tv;
    tv.SetMode(data);
    tv.SetPreambleType(WIFI_PREAMBLE_LONG);
    tv.SetChannelWidth(MHz_u{20});
    tv.SetNss(1);
    Ptr<TableBasedErrorRateModel> model = CreateObject<TableBasedErrorRateModel>();

    const double noiseW = std::pow(10.0, 7.0 / 10.0) * 1.3803e-23 * 290 * 20e6;
    const double snr = std::pow(10.0, (rxPowerDbm - 30.0) / 10.0) / noiseW;
    const double rate = data.GetDataRate(MHz_u{20});
    const auto dbps = static_cast<uint64_t>(std::llround(rate * 4e-6));
    const auto headerBits = static_cast<uint64_t>(header.GetDataRate(MHz_u{20}) * 4e-6);
    const double csrHeader = model->GetChunkSuccessRate(header, tv, snr, headerBits, 1,
                                                        WIFI_PPDU_FIELD_NON_HT_HEADER);

    std::cout << "mode,rx_power_dbm,snr_db,app_bytes,mpdu_bytes,payload_bits,csr_header,"
                 "csr_payload,per\n";
    std::stringstream ss(sizes);
    for (std::string tok; std::getline(ss, tok, ',');)
    {
        const uint64_t app = std::stoul(tok);
        const uint64_t mpdu = app + 36;
        const uint64_t nsym = (16 + 8 * mpdu + 6 + dbps - 1) / dbps;
        const uint64_t nbits = dbps * nsym;
        const double csrPayload =
            model->GetChunkSuccessRate(data, tv, snr, nbits, 1, WIFI_PPDU_FIELD_DATA);
        std::cout << modeName << "," << rxPowerDbm << "," << std::setprecision(6)
                  << 10 * std::log10(snr) << "," << app << "," << mpdu << "," << nbits << ","
                  << std::setprecision(10) << csrHeader << "," << csrPayload << ","
                  << 1.0 - csrHeader * csrPayload << "\n";
    }
    return 0;
}
