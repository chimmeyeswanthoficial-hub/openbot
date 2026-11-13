# Portable toolchain (not kept in the workspace snapshot)

The build sandbox shipped Node 20 with no Bun or pnpm, while Rakazo needs Node ≥24.15 + pnpm
12.18.0 and OpenBot needs Bun ≥1.4. The binaries (~600 MB) were installed, used to verify the
upstreams, then removed so the workspace stays inside its snapshot budget.

```sh
mkdir -p ~/tools && cd ~/tools
V=$(curl -sS https://nodejs.org/dist/index.json | python3 -c "import json,sys;print([x['version'] for x in json.load(sys.stdin) if x['version'].startswith('v24.')][0])")
curl -fsSL -o node24.tar.xz https://nodejs.org/dist/$V/node-$V-linux-x64.tar.xz && tar xf node24.tar.xz && mv node-$V-linux-x64 node24
curl -fsSL -o bun.zip https://github.com/oven-sh/bun/releases/latest/download/bun-linux-x64.zip && mkdir -p bun-linux-x64 && (cd bun-linux-x64 && unzip -oq ../bun.zip)
npm_config_prefix=$HOME/tools "$HOME/tools/node24/bin/npm" i -g pnpm@12.18.0
export PATH="$HOME/tools/node24/bin:$HOME/tools/bin:$HOME/tools/bun-linux-x64:$HOME/.local/bin:$PATH"
```

Meta Muse Code (`muse`, verified 1.4.14 here) installs outside your workspace root:
`MUSE_INSTALL_DIR=/opt/muse bash -c 'curl -fsSL https://dev.meta.ai/install.sh | bash'` — and it
needs `bubblewrap` on Linux or it refuses to run sandboxed.

Full reproduction, including the exact commands and what was verified: `INSTALL_LOG.md`.
