#!/usr/bin/env node

/**
 * Version synchronization script
 * Reads version from ../../VERSION and updates manifest.json and package.json
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read version from VERSION file in project root
const versionPath = path.join(__dirname, '../../VERSION');
const version = fs.readFileSync(versionPath, 'utf8').trim();

console.log(`📦 Updating proxy version to: ${version}`);

// Update manifest.json
const manifestPath = path.join(__dirname, 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
manifest.version = version;
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
console.log(`✅ Updated manifest.json version to ${version}`);

// Update package.json
const packagePath = path.join(__dirname, 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
packageJson.version = version;
fs.writeFileSync(packagePath, JSON.stringify(packageJson, null, 2) + '\n');
console.log(`✅ Updated package.json version to ${version}`);

console.log(`🎉 Version synchronization complete: ${version}`);
