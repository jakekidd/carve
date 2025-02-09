// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title Tree - Stores carvings securely and allows for public gallery submissions.
 * @notice Provides functionality to store, retrieve, and publicize on-chain messages, or carvings into the tree.
 * @dev All write methods are relayer-compatible to ensure easy off-chain management.
 * @dev made with love
 *  ██████╗ █████╗ ██████╗ ██╗   ██╗███████╗
 * ██╔════╝██╔══██╗██╔══██╗██║   ██║██╔════╝
 * ██║     ███████║██████╔╝██║   ██║█████╗  
 * ██║     ██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  
 * ╚██████╗██║  ██║██║  ██║ ╚████╔╝ ███████╗
 * ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝
 */
contract Tree {

    struct Carving {
        string to;          // Who the carving is for.
        string from;        // Who the carving is from.
        bytes32 properties; // Metadata for text display, etc.
        string message;     // The message content.
    }

    /// @notice Mapping of carving IDs to their corresponding carvings.
    mapping(bytes32 => Carving) private _carvings;
    /// @notice Array to store public gallery carving IDs.
    bytes32[] public gallery;
    /// @notice Mapping to manage officiant roles. Officiants can carve and remove.
    mapping(address => bool) public officiants;
    /// @notice Mapping to prevent replay attacks by tracking used signatures.
    mapping(bytes => bool) private _usedSignatures;

    /// @notice Event emitted when a carving is created.
    event CarvingStored(bytes32 indexed carvingId, string to, string from, string message, bytes32 properties);
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
     * @param properties Metadata for the carving (e.g., display styles).
     * @param message The message to be carved.
     */
    function carve(bytes32 carvingId, bytes32 properties, string memory message, string memory to, string memory from) external onlyOfficiant {
        if (bytes(_carvings[carvingId].message).length != 0) revert CarvingExists();
        _carvings[carvingId] = Carving(to, from, properties, message);
        emit CarvingStored(carvingId, to, from, message, properties);
    }

    /**
     * @notice Removes a carving from the contract with relayer validation.
     * @param carvingId The unique ID of the carving to be removed.
     */
    function scratch(bytes32 carvingId) external onlyOfficiant {
        if (bytes(_carvings[carvingId].message).length == 0) revert CarvingNotFound();
        delete _carvings[carvingId];
        emit CarvingDeleted(carvingId);
    }

    /**
     * @notice Adds a carving to the public gallery.
     * @param carvingId The unique ID of the carving to be publicized.
     */
    function publicize(bytes32 carvingId) external onlyOfficiant {
        if (bytes(_carvings[carvingId].message).length == 0) revert CarvingNotFound();
        gallery.push(carvingId);
        emit CarvingPublicized(carvingId);
    }

    /**
     * @notice Removes a carving from the public gallery.
     * @param carvingId The unique ID of the carving to be removed from the gallery.
     */
    function hide(bytes32 carvingId) external onlyOfficiant {
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
     * @return The properties and message associated with the carving ID.
     */
    function read(bytes32 carvingId) external view returns (bytes32, string memory) {
        Carving storage carving = _carvings[carvingId];
        if (bytes(carving.message).length == 0) revert CarvingNotFound();
        return (carving.properties, carving.message);
    }
}
