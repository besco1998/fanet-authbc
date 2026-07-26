# hw/keys/ — NOT for private keys

**`hw/keys/` is git-ignored on purpose. Never commit a private SSH key here or anywhere else in this
repo**, even though the repo is private. A key in git history is a permanent leak: it survives in
every clone and fork, in CI logs, and through any future change of repository visibility. Rotating
the repo's privacy setting does not un-leak it.

## Where keys belong
On each machine, in `~/.ssh/` with the right modes:

```bash
# on your laptop / dev box (generate ONE key per client machine, not per Pi)
ssh-keygen -t ed25519 -C "authbc-dev" -f ~/.ssh/authbc_ed25519
chmod 600 ~/.ssh/authbc_ed25519 && chmod 644 ~/.ssh/authbc_ed25519.pub

# push the PUBLIC key to each Pi
ssh-copy-id -i ~/.ssh/authbc_ed25519.pub pi@authbc-pi4a.local
ssh-copy-id -i ~/.ssh/authbc_ed25519.pub pi@authbc-pi4b.local
```

Then in `~/.ssh/config` on the dev box:
```
Host pi4a
    HostName authbc-pi4a.local
    User pi
    IdentityFile ~/.ssh/authbc_ed25519
Host pi4b
    HostName authbc-pi4b.local
    User pi
    IdentityFile ~/.ssh/authbc_ed25519
```
…so `ssh pi4a` just works, with no key material in the repo.

## If a private key was ever committed or pushed
Treat it as **compromised**:
1. Generate a fresh keypair (above).
2. Remove the old public key from every Pi's `~/.ssh/authorized_keys`.
3. Purge the file from history (`git filter-repo --path hw/keys --invert-paths`, or BFG) and
   force-push — then confirm with `git log --all -- hw/keys`.

## Also: the `pi` account has no password
A passwordless `pi` user with passwordless `sudo` means anyone who can reach the board on the network
owns it (and the boards will sit on a shared lab/campus Wi-Fi during the 802.11 runs). Minimum
hardening, none of which affects measurements:

```bash
sudo passwd pi                                   # set a real password
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh                       # key-only login
```
Keep the SSH daemon and the ad-hoc measurement link on separate interfaces where possible, and do not
expose the Pis to the public internet.
