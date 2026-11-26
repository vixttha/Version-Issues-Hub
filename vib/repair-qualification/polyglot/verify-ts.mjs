import fs from 'node:fs';import {verify} from './verify.ts';verify(...process.argv.slice(2).map(p=>JSON.parse(fs.readFileSync(p,'utf8'))));
