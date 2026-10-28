//! The lean AUTHBC frame (`src/authbc/placement/wire_v2.py`) in compiled code — revision A8.
//!
//! Byte for byte the Python codec's format: a canonical-CBOR map with integer keys 0..7
//! (version, type, src, base_seq, n, link, record stream, signature); the record stream is
//! LEB128 varints (keyframe: `ts`, `battery`, `mode` unsigned, the rest zig-zag; delta: every
//! field zig-zag); the signature covers the canonical CBOR array of the rebuilt record maps
//! (`wire.covered_bytes`, placement B), each record's `prev_hash` derived, never read. The
//! byte-identity gate (`analysis/rust_identity.py`) holds the two codecs equal on 10 000 frames.

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use sha2::{Digest, Sha256};

pub const PAYLOAD_FIELDS: [&str; 8] =
    ["lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode"];
const UNSIGNED: [bool; 9] = [true, false, false, false, false, false, false, true, true];

/// One ledger record: `ts` and the eight payload values in `PAYLOAD_FIELDS` order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Record {
    pub src: u64,
    pub seq: u64,
    pub ts: i64,
    pub prev_hash: [u8; 32],
    pub pl: [i64; 8],
}

// ------------------------------------------------------------------------- canonical CBOR
fn head(out: &mut Vec<u8>, major: u8, v: u64) {
    let m = major << 5;
    if v < 24 {
        out.push(m | v as u8);
    } else if v < 0x100 {
        out.extend_from_slice(&[m | 24, v as u8]);
    } else if v < 0x10000 {
        out.push(m | 25);
        out.extend_from_slice(&(v as u16).to_be_bytes());
    } else if v < 0x1_0000_0000 {
        out.push(m | 26);
        out.extend_from_slice(&(v as u32).to_be_bytes());
    } else {
        out.push(m | 27);
        out.extend_from_slice(&v.to_be_bytes());
    }
}

fn int(out: &mut Vec<u8>, v: i64) {
    if v >= 0 {
        head(out, 0, v as u64);
    } else {
        head(out, 1, (-1 - v) as u64);
    }
}

fn bytes(out: &mut Vec<u8>, b: &[u8]) {
    head(out, 2, b.len() as u64);
    out.extend_from_slice(b);
}

fn text(out: &mut Vec<u8>, s: &str) {
    head(out, 3, s.len() as u64);
    out.extend_from_slice(s.as_bytes());
}

// payload keys in canonical order (shorter first, then bytewise): alt lat lon mode vel_x
// vel_y vel_z battery, with each one's index in PAYLOAD_FIELDS
const PL_ORDER: [(&str, usize); 8] = [
    ("alt", 2), ("lat", 0), ("lon", 1), ("mode", 7), ("vel_x", 3), ("vel_y", 4), ("vel_z", 5),
    ("battery", 6),
];

fn record_map(out: &mut Vec<u8>, r: &Record) {
    head(out, 5, 5); // keys in canonical order: ph pl ts seq src
    text(out, "ph");
    bytes(out, &r.prev_hash);
    text(out, "pl");
    head(out, 5, 8);
    for (name, i) in PL_ORDER {
        text(out, name);
        int(out, r.pl[i]);
    }
    text(out, "ts");
    int(out, r.ts);
    text(out, "seq");
    int(out, r.seq as i64);
    text(out, "src");
    int(out, r.src as i64);
}

/// `Record.canonical()`.
pub fn canonical(r: &Record) -> Vec<u8> {
    let mut out = Vec::with_capacity(160);
    record_map(&mut out, r);
    out
}

/// `Record.record_hash()`: SHA-256 of the canonical bytes.
pub fn record_hash(r: &Record) -> [u8; 32] {
    Sha256::digest(canonical(r)).into()
}

/// What a self-batch frame signs: the canonical CBOR array of the records' maps.
pub fn covered(recs: &[Record]) -> Vec<u8> {
    let mut out = Vec::with_capacity(160 * recs.len());
    head(&mut out, 4, recs.len() as u64);
    for r in recs {
        record_map(&mut out, r);
    }
    out
}

// ------------------------------------------------------------------------- record stream
fn uvarint(out: &mut Vec<u8>, mut u: u64) {
    loop {
        let b = (u & 0x7f) as u8;
        u >>= 7;
        if u == 0 {
            out.push(b);
            return;
        }
        out.push(b | 0x80);
    }
}

fn zigzag(n: i64) -> u64 {
    ((n << 1) ^ (n >> 63)) as u64
}

fn unzigzag(u: u64) -> i64 {
    ((u >> 1) as i64) ^ -((u & 1) as i64)
}

fn read_uvarint(d: &[u8], pos: &mut usize) -> Result<u64, String> {
    let (mut v, mut shift) = (0u64, 0u32);
    loop {
        let b = *d.get(*pos).ok_or("truncated varint")?;
        *pos += 1;
        v |= ((b & 0x7f) as u64) << shift;
        if b & 0x80 == 0 {
            return Ok(v);
        }
        shift += 7;
        if shift > 63 {
            return Err("varint too long".into());
        }
    }
}

fn values(r: &Record) -> [i64; 9] {
    let mut v = [0i64; 9];
    v[0] = r.ts;
    v[1..].copy_from_slice(&r.pl);
    v
}

pub fn record_stream(recs: &[Record]) -> Vec<u8> {
    let mut out = Vec::with_capacity(64);
    let mut last: Option<[i64; 9]> = None;
    for r in recs {
        let vals = values(r);
        match last {
            None => {
                for (k, v) in vals.iter().enumerate() {
                    if UNSIGNED[k] {
                        uvarint(&mut out, *v as u64)
                    } else {
                        uvarint(&mut out, zigzag(*v))
                    }
                }
            }
            Some(prev) => {
                for k in 0..9 {
                    uvarint(&mut out, zigzag(vals[k] - prev[k]));
                }
            }
        }
        last = Some(vals);
    }
    out
}

// ------------------------------------------------------------------------- the frame
/// Encode and sign a self-contained frame (type 1) of consecutive, chained records.
pub fn encode_frame(recs: &[Record], sk: &SigningKey) -> Vec<u8> {
    let sig = sk.sign(&covered(recs));
    let mut out = Vec::with_capacity(200);
    head(&mut out, 5, 8);
    for (k, v) in [(0u64, 2i64), (1, 1), (2, recs[0].src as i64), (3, recs[0].seq as i64),
                   (4, recs.len() as i64)] {
        head(&mut out, 0, k);
        int(&mut out, v);
    }
    head(&mut out, 0, 5);
    bytes(&mut out, &recs[0].prev_hash);
    head(&mut out, 0, 6);
    bytes(&mut out, &record_stream(recs));
    head(&mut out, 0, 7);
    bytes(&mut out, &sig.to_bytes());
    out
}

/// What the sender does per frame, as `wire_v2.encode_frame_v2` does it: check that the records
/// share a sender, run consecutively and chain (one SHA-256 per record, `_check_encodable`),
/// then encode and sign. The work the energy runs meter (A8).
pub fn send_frame(recs: &[Record], sk: &SigningKey) -> Result<Vec<u8>, String> {
    let mut expected = recs[0].prev_hash;
    for (i, r) in recs.iter().enumerate() {
        if r.src != recs[0].src || r.seq != recs[0].seq + i as u64 {
            return Err("records must share the frame's src and have consecutive seq".into());
        }
        if r.prev_hash != expected {
            return Err(format!("record {i} does not chain"));
        }
        expected = record_hash(r);
    }
    Ok(encode_frame(recs, sk))
}

struct Reader<'a> {
    d: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    fn head(&mut self) -> Result<(u8, u64), String> {
        let b = *self.d.get(self.pos).ok_or("truncated")?;
        self.pos += 1;
        let (major, info) = (b >> 5, b & 0x1f);
        let n = match info {
            0..=23 => info as u64,
            24..=27 => {
                let len = 1usize << (info - 24);
                let s = self.d.get(self.pos..self.pos + len).ok_or("truncated")?;
                self.pos += len;
                s.iter().fold(0u64, |a, &x| (a << 8) | x as u64)
            }
            _ => return Err("indefinite or reserved length".into()),
        };
        Ok((major, n))
    }

    fn uint(&mut self) -> Result<u64, String> {
        match self.head()? {
            (0, n) => Ok(n),
            _ => Err("expected an unsigned integer".into()),
        }
    }

    fn bstr(&mut self) -> Result<&'a [u8], String> {
        match self.head()? {
            (2, n) => {
                let s = self.d.get(self.pos..self.pos + n as usize).ok_or("truncated")?;
                self.pos += n as usize;
                Ok(s)
            }
            _ => Err("expected a byte string".into()),
        }
    }
}

/// A decoded self-contained frame: its records rebuilt, and its signature.
pub struct Frame {
    pub recs: Vec<Record>,
    pub sig: [u8; 64],
}

/// Decode a type-1 frame and rebuild its records (`wire_v2.decode_frame_v2`, `prev=None`).
pub fn decode_frame(data: &[u8]) -> Result<Frame, String> {
    let mut r = Reader { d: data, pos: 0 };
    if r.head()? != (5, 8) {
        return Err("frame must be a map of eight".into());
    }
    let mut f = [0u64; 5];
    for (k, slot) in f.iter_mut().enumerate() {
        if r.uint()? != k as u64 {
            return Err("keys out of order".into());
        }
        *slot = r.uint()?;
    }
    if f[0] != 2 || f[1] != 1 {
        return Err("only version 2, type 1 frames are handled here".into());
    }
    let (src, base_seq, n) = (f[2], f[3], f[4] as usize);
    if r.uint()? != 5 {
        return Err("key 5".into());
    }
    let link: [u8; 32] = r.bstr()?.try_into().map_err(|_| "link must be 32 bytes")?;
    if r.uint()? != 6 {
        return Err("key 6".into());
    }
    let stream = r.bstr()?;
    if r.uint()? != 7 {
        return Err("key 7".into());
    }
    let sig: [u8; 64] = r.bstr()?.try_into().map_err(|_| "signature must be 64 bytes")?;
    if r.pos != data.len() || !(1..=255).contains(&n) {
        return Err("trailing bytes or bad record count".into());
    }
    let mut recs = Vec::with_capacity(n);
    let (mut pos, mut ph) = (0usize, link);
    let mut last: Option<[i64; 9]> = None;
    for i in 0..n {
        let mut vals = [0i64; 9];
        for k in 0..9 {
            let u = read_uvarint(stream, &mut pos)?;
            vals[k] = match last {
                None if UNSIGNED[k] => u as i64,
                None => unzigzag(u),
                Some(prev) => prev[k] + unzigzag(u),
            };
        }
        let mut pl = [0i64; 8];
        pl.copy_from_slice(&vals[1..]);
        let rec = Record { src, seq: base_seq + i as u64, ts: vals[0], prev_hash: ph, pl };
        ph = record_hash(&rec);
        recs.push(rec);
        last = Some(vals);
    }
    if pos != stream.len() {
        return Err("trailing bytes after the last record".into());
    }
    Ok(Frame { recs, sig })
}

/// Verify a decoded frame's one signature over its rebuilt records.
pub fn verify(frame: &Frame, pk: &VerifyingKey) -> bool {
    pk.verify(&covered(&frame.recs), &Signature::from_bytes(&frame.sig)).is_ok()
}

/// Verify many frames at once (Ed25519 batch verification); true iff all verify.
pub fn verify_batch(frames: &[Frame], pk: &VerifyingKey) -> bool {
    let msgs: Vec<Vec<u8>> = frames.iter().map(|f| covered(&f.recs)).collect();
    let refs: Vec<&[u8]> = msgs.iter().map(|m| m.as_slice()).collect();
    let sigs: Vec<Signature> = frames.iter().map(|f| Signature::from_bytes(&f.sig)).collect();
    let keys = vec![*pk; frames.len()];
    ed25519_dalek::verify_batch(&refs, &sigs, &keys).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chained(n: usize) -> Vec<Record> {
        let mut out: Vec<Record> = Vec::new();
        let mut ph = [0u8; 32];
        for i in 0..n {
            let r = Record { src: 7, seq: 100 + i as u64, ts: 3_600_000 + 20 * i as i64,
                             prev_hash: ph, pl: [473977420 + i as i64, 85455940, 4880, 120,
                                                 -40, 3, 87, 3] };
            ph = record_hash(&r);
            out.push(r);
        }
        out
    }

    #[test]
    fn send_frame_is_encode_frame_on_a_chained_run() {
        let sk = SigningKey::from_bytes(&[7u8; 32]);
        let recs = chained(8);
        for chunk in recs.chunks(4) {
            assert_eq!(send_frame(chunk, &sk).unwrap(), encode_frame(chunk, &sk));
        }
    }

    #[test]
    fn send_frame_refuses_records_that_do_not_chain() {
        let sk = SigningKey::from_bytes(&[7u8; 32]);
        let mut recs = chained(4);
        recs[2].prev_hash[0] ^= 1;                 // as wire_v2._check_encodable refuses
        assert!(send_frame(&recs, &sk).is_err());
        let mut recs = chained(4);
        recs[3].seq += 1;
        assert!(send_frame(&recs, &sk).is_err());
    }
}
