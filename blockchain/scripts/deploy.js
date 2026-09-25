/**
 * Deploys the single PramaanXRegistry contract to the local EVM and writes
 * the ABI + address to disk so the Python web3.py service can load them.
 *
 * Usage:
 *   1. Terminal A:  npx hardhat node
 *   2. Terminal B:  npx hardhat run scripts/deploy.js --network localhost
 */
const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const Registry = await hre.ethers.getContractFactory("PramaanXRegistry");
  const registry = await Registry.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  console.log("PramaanXRegistry deployed to:", address);

  // Persist artifacts one level up (blockchain/) for the Python service and
  // for teammate handover. contract_abi.json is a committed deliverable;
  // deployed_address.json is environment-specific.
  const outDir = path.resolve(__dirname, "..");
  const artifact = await hre.artifacts.readArtifact("PramaanXRegistry");

  fs.writeFileSync(
    path.join(outDir, "contract_abi.json"),
    JSON.stringify(artifact.abi, null, 2) + "\n"
  );
  fs.writeFileSync(
    path.join(outDir, "deployed_address.json"),
    JSON.stringify(
      {
        address,
        network: hre.network.name,
        deployedAt: new Date().toISOString(),
      },
      null,
      2
    ) + "\n"
  );

  console.log("Wrote contract_abi.json and deployed_address.json to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
