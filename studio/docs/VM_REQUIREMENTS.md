# Real per-bot computers, not renamed folders

The user requested a virtual PC for each bot with Claude Code, Antigravity IDE and
T3 Code. This extension can request those tools and produce individual setup
blueprints. It **does not provision computers or install any tool**.

## Current observed environment

The local host observation checks binary/device **presence only**, without running
hypervisors, installers, containers or remote APIs. At this engineering checkpoint,
QEMU, virsh, Docker and `/dev/kvm` were not detected. This is not a claim about the
user's own PC, all cloud hosts, or Arena's general capabilities.

A 0700 local blueprint directory is a real directory, not a VM. The kernel's tested
rootless namespace experiment is a bounded fixed-tool process, not a desktop guest
or evidence of hostile-tenant isolation. A Bot HQ computer card, an OpenDots service
reference or a requested IDE name does not make a usable session exist.

## Blueprint, not enforcement

Each companion requests its own guest OS, no host mounts, no secret material and
default-deny network. Example sizes (2 vCPU / 4 GiB RAM / 32 GiB disk) are **not
allocated, reserved or enforced**. There is no start endpoint or host fallback.

## Before implementing provisioning

1. Owner chooses an actual local/cloud VM host, operating system, billing account,
   cost cap and retention policy. Selecting a host is not authorization to spend.
2. Use an appropriately licensed, immutable/pinned OS image and reviewed hypervisor
   driver. Verify architecture, nested virtualization availability and image origin.
3. Give each bot distinct machine, disk, network identity and scoped control-plane
   grants; no shared administrator key, Docker socket or writable host repository.
4. Keep account/model/IDE/deploy credentials in a broker outside the guest's writable
   files. Grant short-lived least-purpose access and prove cross-bot denial.
5. Install only verified/pinned IDE distributions compatible with the chosen OS.
   Claude Code, Antigravity IDE and T3 Code each need distribution, license/terms,
   authentication and provider-cost review. No guessed install command is included.
6. Enforce actual CPU/RAM/disk/time/network limits and reserve costs independently.
   Make stop/kill/expiry, reconnect, destructive reset and restore explicit.
7. Test guest escape boundaries, cross-bot files/secrets, egress, runaway subprocesses,
   interruption, crash recovery and orphaned billable machines. Use qualified external
   security review before treating virtual-PC isolation as accepted.
8. Bind install/start/stop/destroy approvals to an exact bot, image/tool version,
   target host, budget and expiry; never let a companion relax its own controls.

Only a verified provisioner receipt and a real authenticated session can change
“not provisioned” or “not installed” into an operating status. This build has neither.
