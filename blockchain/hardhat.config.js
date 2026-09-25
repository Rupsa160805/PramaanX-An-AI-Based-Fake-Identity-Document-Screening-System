require("@nomicfoundation/hardhat-ethers");

/**
 * Hardhat configuration for the PramaanX blockchain core (P1).
 *
 * Local-only EVM. No public networks, no paid RPC, no mainnet — per the
 * sprint scope rules. `npx hardhat node` starts a local chain on
 * http://127.0.0.1:8545 with pre-funded unlocked accounts.
 */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    // Attach to a running `npx hardhat node` instance.
    localhost: {
      url: "http://127.0.0.1:8545",
    },
  },
};
