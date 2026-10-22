//! `authbc-rx` — the compiled codec's command line (revision A8).
//!
//!   authbc-rx encode  RECORDS.jsonl SK_HEX BATCH  > FRAMES.bin   sign frames of BATCH records
//!   authbc-rx verify  FRAMES.bin PK_HEX                          decode, rebuild, verify each
//!   authbc-rx bench   FRAMES.bin PK_HEX REPS                     time the receive path
//!   authbc-rx lazy    FRAMES.bin PK_HEX REPS                     time the two tiers (A13)
//!   authbc-rx sendbench RECORDS.jsonl SK_HEX BATCH REPS          time the sender per frame (A8)
//!   authbc-rx sendloop  RECORDS.jsonl SK_HEX BATCH SECONDS       send back to back for a metered
//!                                                                window; prints frames made (A8)
//!
//! A frames file is a sequence of (u32 big-endian length, frame bytes). A records file has one
//! JSON object per line: {"src", "seq", "ts", "ph" (hex), "pl": [lat, lon, alt, vel_x, vel_y,
//! vel_z, battery, mode]}.

use authbc_rx::{decode_frame, encode_frame, send_frame, verify, verify_batch, Frame, Record};
use ed25519_dalek::{SigningKey, VerifyingKey};
use std::io::{Read, Write};
use std::time::Instant;

fn read_frames(path: &str) -> Vec<Vec<u8>> {
    let mut data = Vec::new();
    std::fs::File::open(path).expect("frames file").read_to_end(&mut data).unwrap();
    let mut out = Vec::new();
    let mut pos = 0;
    while pos + 4 <= data.len() {
        let n = u32::from_be_bytes(data[pos..pos + 4].try_into().unwrap()) as usize;
        out.push(data[pos + 4..pos + 4 + n].to_vec());
        pos += 4 + n;
    }
    out
}

fn read_records(path: &str) -> Vec<Record> {
    let text = std::fs::read_to_string(path).expect("records file");
    text.lines()
        .map(|l| {
            let v: serde_json::Value = serde_json::from_str(l).unwrap();
            let mut pl = [0i64; 8];
            for (k, x) in v["pl"].as_array().unwrap().iter().enumerate() {
                pl[k] = x.as_i64().unwrap();
            }
            Record {
                src: v["src"].as_u64().unwrap(),
                seq: v["seq"].as_u64().unwrap(),
                ts: v["ts"].as_i64().unwrap(),
                prev_hash: key32(v["ph"].as_str().unwrap()),
                pl,
            }
        })
        .collect()
}

fn key32(hex_str: &str) -> [u8; 32] {
    hex::decode(hex_str).expect("hex").try_into().expect("32 bytes")
}

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    v[v.len() / 2]
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("encode") => {
            let sk = SigningKey::from_bytes(&key32(&args[3]));
            let batch: usize = args[4].parse().unwrap();
            let recs = read_records(&args[2]);
            let mut out = std::io::stdout().lock();
            for chunk in recs.chunks(batch) {
                if chunk.len() < batch {
                    break;
                }
                let f = encode_frame(chunk, &sk);
                out.write_all(&(f.len() as u32).to_be_bytes()).unwrap();
                out.write_all(&f).unwrap();
            }
        }
        Some("verify") => {
            let pk = VerifyingKey::from_bytes(&key32(&args[3])).expect("public key");
            let frames = read_frames(&args[2]);
            let ok = frames
                .iter()
                .filter(|f| decode_frame(f).map(|fr| verify(&fr, &pk)).unwrap_or(false))
                .count();
            println!("{ok} of {} frames decode and verify", frames.len());
        }
        Some("bench") => {
            let pk = VerifyingKey::from_bytes(&key32(&args[3])).expect("public key");
            let frames = read_frames(&args[2]);
            let reps: usize = args[4].parse().unwrap();
            let (mut per_frame, mut decode_only) = (Vec::new(), Vec::new());
            for _ in 0..reps {
                let t = Instant::now();
                for f in &frames {
                    let fr = decode_frame(f).unwrap();
                    assert!(verify(&fr, &pk));
                }
                per_frame.push(t.elapsed().as_nanos() as f64 / frames.len() as f64);
                let t = Instant::now();
                for f in &frames {
                    std::hint::black_box(decode_frame(f).unwrap());
                }
                decode_only.push(t.elapsed().as_nanos() as f64 / frames.len() as f64);
            }
            let decoded: Vec<Frame> = frames.iter().map(|f| decode_frame(f).unwrap()).collect();
            let mut batch64 = Vec::new();
            for _ in 0..reps {
                let t = Instant::now();
                for chunk in decoded.chunks(64) {
                    assert!(verify_batch(chunk, &pk));
                }
                batch64.push(t.elapsed().as_nanos() as f64 / decoded.len() as f64);
            }
            println!("receive_ns_per_frame,{:.0}", median(per_frame));
            println!("decode_rebuild_ns_per_frame,{:.0}", median(decode_only));
            println!("batch64_verify_ns_per_frame,{:.0}", median(batch64));
            println!("frames,{}", frames.len());
        }
        Some("lazy") => {
            // Revision A13: a real-time tier (an 8 B group tag, then decode and rebuild: the
            // records are usable at once) and an evidence tier (Ed25519 in batches of 64, as
            // the ledger is written). The tags are made here, as the senders would make them;
            // only their checking is timed.
            use hmac::{Hmac, Mac};
            type HmacSha256 = Hmac<sha2::Sha256>;
            let pk = VerifyingKey::from_bytes(&key32(&args[3])).expect("public key");
            let frames = read_frames(&args[2]);
            let reps: usize = args[4].parse().unwrap();
            let key = b"swarm group key (A13 bench)";
            let tag = |f: &[u8]| {
                let mut m = HmacSha256::new_from_slice(key).unwrap();
                m.update(f);
                m.finalize().into_bytes()[..8].to_vec()
            };
            let tagged: Vec<(Vec<u8>, &Vec<u8>)> = frames.iter().map(|f| (tag(f), f)).collect();
            let (mut tier1, mut tier2) = (Vec::new(), Vec::new());
            for _ in 0..reps {
                let t = Instant::now();
                let mut decoded = Vec::with_capacity(frames.len());
                for (t8, f) in &tagged {
                    let mut m = HmacSha256::new_from_slice(key).unwrap();
                    m.update(f);
                    m.verify_truncated_left(t8).expect("tag");
                    decoded.push(decode_frame(f).unwrap());
                }
                tier1.push(t.elapsed().as_nanos() as f64 / frames.len() as f64);
                let t = Instant::now();
                for chunk in decoded.chunks(64) {
                    assert!(verify_batch(chunk, &pk));
                }
                tier2.push(t.elapsed().as_nanos() as f64 / frames.len() as f64);
            }
            println!("tier1_tag_decode_ns_per_frame,{:.0}", median(tier1));
            println!("tier2_batch64_ns_per_frame,{:.0}", median(tier2));
            println!("frames,{}", frames.len());
        }
        Some("sendbench") => {
            let sk = SigningKey::from_bytes(&key32(&args[3]));
            let batch: usize = args[4].parse().unwrap();
            let reps: usize = args[5].parse().unwrap();
            let recs = read_records(&args[2]);
            let groups: Vec<&[Record]> = recs.chunks_exact(batch).collect();
            let mut per_frame = Vec::new();
            for _ in 0..reps {
                let t = Instant::now();
                for g in &groups {
                    std::hint::black_box(send_frame(g, &sk).unwrap());
                }
                per_frame.push(t.elapsed().as_nanos() as f64 / groups.len() as f64);
            }
            println!("send_ns_per_frame,{:.0}", median(per_frame));
            println!("frames,{}", groups.len());
        }
        Some("sendloop") => {
            // One metered window (A8 energy): frames back to back for SECONDS, cycling through
            // the records; the records are read before the clock starts.
            let sk = SigningKey::from_bytes(&key32(&args[3]));
            let batch: usize = args[4].parse().unwrap();
            let seconds: f64 = args[5].parse().unwrap();
            let recs = read_records(&args[2]);
            let groups: Vec<&[Record]> = recs.chunks_exact(batch).collect();
            let (mut n, mut checksum) = (0u64, 0u64);
            let t = Instant::now();
            while t.elapsed().as_secs_f64() < seconds {
                let f = send_frame(groups[n as usize % groups.len()], &sk).unwrap();
                checksum = checksum.wrapping_mul(1_000_003).wrapping_add(f[f.len() - 1] as u64);
                n += 1;
            }
            println!("frames,{n}");
            println!("seconds,{:.6}", t.elapsed().as_secs_f64());
            println!("checksum,{checksum}");
        }
        _ => {
            eprintln!("usage: authbc-rx encode|verify|bench|lazy|sendbench|sendloop ...");
            std::process::exit(2);
        }
    }
}
