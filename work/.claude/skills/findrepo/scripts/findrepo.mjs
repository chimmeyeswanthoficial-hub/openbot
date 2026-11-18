#!/usr/bin/env node
import { main } from '../../../../tools/findrepo/skills/findrepo/scripts/findrepo.mjs';
main(process.argv.slice(2)).catch(e => { console.error(e.message); process.exitCode = 1; });
