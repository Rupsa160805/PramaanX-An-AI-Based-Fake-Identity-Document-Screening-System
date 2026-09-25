// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title PramaanXRegistry
/// @notice Minimal, append-only integrity anchor for the PramaanX
///         three-checkpoint hash chain: INPUT -> ANALYSIS -> FINAL.
///
///         This contract is the ONLY blockchain component for the sprint.
///         It stores nothing but hashes and non-sensitive metadata. Document
///         images, face images, biometric templates, passport numbers, DOB,
///         addresses and any other PII are NEVER written here — that data
///         stays in PramaanX's existing secure storage.
///
///         The contract provides exactly the three required operations:
///         saveRecord(), getRecord(), verifyRecord(). Nothing more.
contract PramaanXRegistry {
    struct Record {
        string recordHash;   // SHA-256 hex of the canonical record payload
        string previousHash; // hash of the previous link ("" for INPUT / H1)
        uint256 timestamp;   // block timestamp when the anchor was written
        bool exists;         // true once anchored
    }

    // verificationId => recordType ("INPUT" | "ANALYSIS" | "FINAL") => Record
    mapping(string => mapping(string => Record)) private records;

    /// @notice Emitted whenever a new hash is anchored on-chain.
    event RecordSaved(
        string indexed verificationId,
        string indexed recordType,
        string recordHash,
        string previousHash,
        uint256 timestamp
    );

    /// @notice Anchor a record hash on-chain.
    /// @dev First-write-wins. An existing (verificationId, recordType) anchor
    ///      cannot be overwritten — that is what makes the anchor
    ///      tamper-evident. Re-anchoring the same checkpoint reverts.
    /// @param verificationId Logical id of the verification (e.g. "PX001").
    /// @param recordType One of "INPUT", "ANALYSIS", "FINAL".
    /// @param recordHash SHA-256 hex computed by the BACKEND (never the client).
    /// @param previousHash Hash of the previous checkpoint ("" for INPUT).
    function saveRecord(
        string calldata verificationId,
        string calldata recordType,
        string calldata recordHash,
        string calldata previousHash
    ) external {
        require(bytes(verificationId).length > 0, "verificationId required");
        require(bytes(recordType).length > 0, "recordType required");
        require(bytes(recordHash).length > 0, "recordHash required");
        require(
            !records[verificationId][recordType].exists,
            "record already anchored"
        );

        records[verificationId][recordType] = Record({
            recordHash: recordHash,
            previousHash: previousHash,
            timestamp: block.timestamp,
            exists: true
        });

        emit RecordSaved(
            verificationId,
            recordType,
            recordHash,
            previousHash,
            block.timestamp
        );
    }

    /// @notice Read a previously anchored record.
    /// @return recordHash The anchored SHA-256 hex ("" if not found).
    /// @return previousHash The anchored previous-hash link.
    /// @return timestamp Block timestamp of the anchor (0 if not found).
    /// @return exists True only if the record was anchored.
    function getRecord(string calldata verificationId, string calldata recordType)
        external
        view
        returns (
            string memory recordHash,
            string memory previousHash,
            uint256 timestamp,
            bool exists
        )
    {
        Record storage r = records[verificationId][recordType];
        return (r.recordHash, r.previousHash, r.timestamp, r.exists);
    }

    /// @notice Compare a freshly recomputed hash against the anchored hash.
    /// @return True only when the record exists AND the hashes are identical.
    ///         A false result means MISMATCH (or never anchored). It does NOT
    ///         say who changed the data, and it does NOT judge AI correctness.
    function verifyRecord(
        string calldata verificationId,
        string calldata recordType,
        string calldata recordHash
    ) external view returns (bool) {
        Record storage r = records[verificationId][recordType];
        if (!r.exists) {
            return false;
        }
        return keccak256(bytes(r.recordHash)) == keccak256(bytes(recordHash));
    }
}
