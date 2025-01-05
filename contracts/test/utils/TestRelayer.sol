// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/**
 * @title TestRelayer - A contract to simulate relayer interactions with any target contract.
 * @notice This contract is used for testing relayer functionality by accepting signatures and arguments,
 * and calling the corresponding methods on a target contract.
 */
contract TestRelayer {

    /**
     * @notice Relays a carve request to the target contract.
     * @param target The address of the target contract.
     * @param carvingId The unique ID of the carving.
     * @param message The message to be carved.
     * @param signature The ECDSA signature from an officiant.
     */
    function relayCarve(address target, bytes32 carvingId, string memory message, bytes memory signature) external {
        (bool success, ) = target.call(
            abi.encodeWithSignature("carve(bytes32,string,bytes)", carvingId, message, signature)
        );
        require(success, "Carve relay failed");
    }

    /**
     * @notice Relays a scratch request to the target contract.
     * @param target The address of the target contract.
     * @param carvingId The unique ID of the carving to be removed.
     * @param signature The ECDSA signature from an officiant.
     */
    function relayScratch(address target, bytes32 carvingId, bytes memory signature) external {
        (bool success, ) = target.call(
            abi.encodeWithSignature("scratch(bytes32,bytes)", carvingId, signature)
        );
        require(success, "Scratch relay failed");
    }

    /**
     * @notice Relays a publicize request to the target contract.
     * @param target The address of the target contract.
     * @param carvingId The unique ID of the carving to be publicized.
     * @param signature The ECDSA signature from an officiant.
     */
    function relayPublicize(address target, bytes32 carvingId, bytes memory signature) external {
        (bool success, ) = target.call(
            abi.encodeWithSignature("publicize(bytes32,bytes)", carvingId, signature)
        );
        require(success, "Publicize relay failed");
    }
}
