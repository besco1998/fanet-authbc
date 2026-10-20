//! `authbc-rx` — the compiled codec's command line (revision A8).
//!
//!   authbc-rx encode  RECORDS.jsonl SK_HEX BATCH  > FRAMES.bin   sign frames of BATCH records
//!   authbc-rx verify  FRAMES.bin PK_HEX                          decode, rebuild, verify each
//!   authbc-rx bench   FRAMES.bin PK_HEX REPS                     time the receive path
//!
//! A frames file is a sequence of (u32 big-endian length, frame bytes). A records file has one
//! JSON object per line: {"src", "seq", "ts", "ph" (hex), "pl": [lat, lon, alt, vel_x, vel_y,
//! vel_z, battery, mode]}.

use authbc_rx::{decode_frame, encode_frame, verify, verify_batch, Frame, Record};
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
            let text = std::fs::read_to_string(&args[2]).expect("records file");
            let recs: Vec<Record> = text
                .lines()
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
                .collect();
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
        _ => {
            eprintln!("usage: authbc-rx encode|verify|bench ...");
            std::process::exit(2);
        }
    }
}
