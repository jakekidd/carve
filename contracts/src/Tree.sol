// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title Tree - Stores carvings securely and allows for public gallery submissions.
 * @notice Provides functionality to store, retrieve, and publicize on-chain messages, or carvings into the tree.
 * @dev All write methods are relayer-compatible to ensure easy off-chain management.
 * @dev made with love
 *       .....           .....
 *   ,ad8PPPP88b,     ,d88PPPP8ba,
 *  d8P"      "Y8b, ,d8P"      "Y8b
 * dP'           "8a8"           `Yd
 * 8(              "              )8
 * I8                             8I
 *  Yb,           LFG           ,dP
 *   "8a,                     ,a8"
 *     "8a,                 ,a8"
 *       "Yba             adP"
 *         `Y8a         a8P'
 *           `88,     ,88'
 *             "8b   d8"
 *              "8b d8"
 *               `888'
 *                 "
 */
contract Tree {
    /// @notice Mapping of carving IDs to their corresponding messages.
    mapping(bytes32 => string) private _carvings;
    /// @notice Array to store public gallery carving IDs.
    bytes32[] public gallery;
    /// @notice Tracks the nonce for each carving ID (to prevent replay attacks in gallery actions).
    mapping(bytes32 => uint256) public galleryNonces;
    /// @notice Mapping to manage officiant roles. Officiants can carve and remove.
    mapping(address => bool) public officiants;
    /// @notice Mapping to prevent replay attacks by tracking used signatures.
    mapping(bytes => bool) private _usedSignatures;

    /// @notice Event emitted when a carving is created.
    event CarvingStored(bytes32 indexed carvingId, string message);
    /// @notice Event emitted when a carving is removed.
    event CarvingDeleted(bytes32 indexed carvingId);
    /// @notice Event emitted when a carving is added to the gallery.
    event CarvingPublicized(bytes32 indexed carvingId);
    /// @notice Event emitted when a carving is removed from the gallery.
    event CarvingHidden(bytes32 indexed carvingId);

    /// @notice Custom errors for access control and state validation.
    error NotOfficiant();
    error CarvingExists();
    error CarvingNotFound();
    error CannotDismissSelf();
    error InvalidSignature();
    error SignatureAlreadyUsed();

    /// @notice Modifier to restrict access to officiants.
    modifier onlyOfficiant() {
        if (!officiants[msg.sender]) revert NotOfficiant();
        _;
    }

    constructor() {
        officiants[msg.sender] = true;  // Assign deployer as the first officiant.
    }

    /// OFFICIANT METHODS
    /**
     * @notice Adds a new officiant.
     * @param newOfficiant The address to be added as an officiant.
     */
    function appoint(address newOfficiant) external onlyOfficiant {
        officiants[newOfficiant] = true;
    }

    /**
     * @notice Removes an officiant.
     * @param officiant The address to be removed from officiant roles.
     */
    function dismiss(address officiant) external onlyOfficiant {
        if (officiant == msg.sender) revert CannotDismissSelf();
        officiants[officiant] = false;
    }

    /**
     * @notice Stores a new carving in the contract with relayer validation.
     * @param carvingId The unique ID of the carving.
     * @param message The message to be carved.
     * @param signature The ECDSA signature from an officiant.
     */
    function carve(bytes32 carvingId, string memory message, bytes memory signature) external {
        _verifySignature(carvingId, message, signature);
        if (bytes(_carvings[carvingId]).length != 0) revert CarvingExists();
        _carvings[carvingId] = message;
        emit CarvingStored(carvingId, message);
    }

    /**
     * @notice Removes a carving from the contract with relayer validation.
     * @param carvingId The unique ID of the carving to be removed.
     * @param signature The ECDSA signature from an officiant.
     */
    function scratch(bytes32 carvingId, bytes memory signature) external {
        _verifySignature(carvingId, "", signature);
        if (bytes(_carvings[carvingId]).length == 0) revert CarvingNotFound();
        delete _carvings[carvingId];
        emit CarvingDeleted(carvingId);
    }

    /**
     * @notice Adds a carving to the public gallery.
     * @param carvingId The unique ID of the carving to be publicized.
     */
    function publicize(bytes32 carvingId, bytes memory signature) external onlyOfficiant {
        _verifySignature(carvingId, signature);
        if (bytes(_carvings[carvingId]).length == 0) revert CarvingNotFound();
        gallery.push(carvingId);
        emit CarvingPublicized(carvingId);
    }

    /**
     * @notice Removes a carving from the public gallery.
     * @param carvingId The unique ID of the carving to be removed from the gallery.
     */
    function hide(bytes32 carvingId, bytes memory signature) external onlyOfficiant {
        _verifySignature(carvingId, signature);
        for (uint256 i = 0; i < gallery.length; i++) {
            if (gallery[i] == carvingId) {
                gallery[i] = gallery[gallery.length - 1];
                gallery.pop();
                emit CarvingHidden(carvingId);
                return;
            }
        }
        revert CarvingNotFound();
    }

    /// PUBLIC METHODS
    /**
     * @notice Returns the list of all public carvings in the gallery.
     * @return gallery An array of carving IDs.
     */
    function peruse() external view returns (bytes32[] memory) {
        return gallery;
    }

    /**
     * @notice Retrieves a carving by its unique ID.
     * @param carvingId The unique ID of the carving.
     * @return The message associated with the carving ID.
     */
    function read(bytes32 carvingId) external view returns (string memory) {
        if (bytes(_carvings[carvingId]).length == 0) revert CarvingNotFound();
        return _carvings[carvingId];
    }

    /// PRIVATE METHODS
    /**
     * @notice Verifies an ECDSA signature from an officiant.
     * @param carvingId The unique ID of the carving.
     * @param message The message to be carved.
     * @param signature The ECDSA signature to verify.
     * @dev Ensures the signature is valid and not previously used.
     */
    function _verifySignature(bytes32 carvingId, string memory message, bytes memory signature) private {
        if (signature.length == 0) {
            if (!officiants[msg.sender]) revert NotOfficiant();
            return;
        }
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, message));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        address signer = ECDSA.recover(ethSignedMessageHash, signature);
        if (!officiants[signer]) revert InvalidSignature();
        if (_usedSignatures[signature]) revert SignatureAlreadyUsed();
        _usedSignatures[signature] = true;
    }

    /**
     * @notice Verifies an ECDSA signature from an officiant using gallery nonce.
     * @param carvingId The unique ID of the carving.
     * @param signature The ECDSA signature to verify.
     * @dev Ensures the signature is valid, not previously used, and includes the current nonce. 
     */
    function _verifySignature(
        bytes32 carvingId,
        bytes memory signature
    ) private {
        if (signature.length == 0) {
            if (!officiants[msg.sender]) revert NotOfficiant();
            return;
        }

        uint256 nonce = galleryNonces[carvingId];
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, nonce));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        address signer = ECDSA.recover(ethSignedMessageHash, signature);

        if (!officiants[signer]) revert InvalidSignature();
        if (_usedSignatures[signature]) revert SignatureAlreadyUsed();
        // Mark signature as used and increment gallery nonce.
        _usedSignatures[signature] = true;
        galleryNonces[carvingId] = nonce + 1;
    }
}
