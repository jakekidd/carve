// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

/**
 * @title                       Tree - Stores carvings securely and allows for public gallery submissions.
 * @notice                      Provides functionality to store, retrieve, and publicize on-chain messages, or carvings into the tree.
 * @dev                         All write methods are relayer-compatible to ensure easy off-chain management.
 * @dev                         made with love
 *                               ██████╗ █████╗ ██████╗ ██╗   ██╗███████╗
 *                              ██╔════╝██╔══██╗██╔══██╗██║   ██║██╔════╝
 *                              ██║     ███████║██████╔╝██║   ██║█████╗  
 *                              ██║     ██╔══██║██╔══██╗╚██╗ ██╔╝██╔══╝  
 *                              ╚██████╗██║  ██║██║  ██║ ╚████╔╝ ███████╗
 *                               ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝
 */
contract Tree {
    enum CarvingStatus { free, created, published, deleted }

    struct Carving {
        CarvingStatus status;   // Carving status
        bytes31 properties;     // Metadata for text display, etc.
        string to;              // Who the carving is for.
        string from;            // Who the carving is from.
        string message;         // The message content.
    }

    /// @notice                 Mapping of carving IDs to their corresponding carvings.
    mapping(bytes32 => Carving) private _carvings;
    /// @notice                 Array to store public gallery carving IDs.
    bytes32[] public gallery;
    /// @notice                 Mapping to manage officiant roles. Officiants can modify state.
    mapping(address => bool) public officiants;

    /// @notice                 Event emitted when a carving is created.
    event CarvingStored(bytes32 indexed carvingId, string to, string from, string message, bytes31 properties);
    /// @notice                 Event emitted when a carving is removed.
    event CarvingDeleted(bytes32 indexed carvingId);
    /// @notice                 Event emitted when a carving is added to the gallery.
    event CarvingPublicized(bytes32 indexed carvingId);
    /// @notice                 Event emitted when a carving is removed from the gallery.
    event CarvingHidden(bytes32 indexed carvingId);

    /// @notice                 Custom errors for access control and state validation.
    error NotOfficiant();
    error CannotDismissSelf();
    error CarvingExists();
    error MessageCannotBeEmpty();
    error CarvingNotFound();
    error CarvingNotInGallery();
    error CarvingAlreadyPublished();

    /// @notice                 Modifier to restrict access to officiants.
    modifier onlyOfficiant() {
        if (!officiants[msg.sender]) revert NotOfficiant();
        _;
    }

    /// @notice                 Assign deployer as the first officiant.
    constructor() {
        officiants[msg.sender] = true;
    }

    /// OFFICIANT METHODS
    /**
     * @notice                  Adds a new officiant.
     * @param newOfficiant      The address to be added as an officiant.
     */
    function appoint(address newOfficiant) external onlyOfficiant {
        officiants[newOfficiant] = true;
    }

    /**
     * @notice                  Removes an officiant.
     * @param officiant         The address to be removed from officiant roles.
     */
    function dismiss(address officiant) external onlyOfficiant {
        if (officiant == msg.sender) revert CannotDismissSelf();
        officiants[officiant] = false;
    }

    /**
     * @notice                  Stores a new carving in the contract.
     * @param carvingId         The unique ID of the carving.
     * @param to                Who the carving is for.
     * @param from              Who the carving is from.
     * @param message           The message to be carved.
     * @param properties        Metadata for the carving (e.g., display styles).
     */
    function carve(bytes32 carvingId, string calldata to, string calldata from, string calldata message, bytes31 properties) external onlyOfficiant {
        if (_carvings[carvingId].status != CarvingStatus.free) revert CarvingExists();
        if (bytes(message).length == 0) revert MessageCannotBeEmpty();
        _carvings[carvingId] = Carving({status:CarvingStatus.created, to:to, from:from, message:message, properties:properties});
        emit CarvingStored({carvingId:carvingId, to:to, from:from, message:message, properties:properties});
    }

    /**
     * @notice                  Removes a carving from the contract.
     * @param carvingId         The unique ID of the carving to be removed.
     */
    function scratch(bytes32 carvingId) external onlyOfficiant {
        if (_carvings[carvingId].status == CarvingStatus.published) hide(carvingId);
        if (_carvings[carvingId].status != CarvingStatus.created) revert CarvingNotFound();
        _carvings[carvingId] = Carving({status:CarvingStatus.deleted, to:"", from:"", message:"", properties:0});
        emit CarvingDeleted(carvingId);
    }

    /**
     * @notice                  Adds a carving to the public gallery.
     * @param carvingId         The unique ID of the carving to be publicized.
     */
    function publicize(bytes32 carvingId) external onlyOfficiant {
        if (_carvings[carvingId].status == CarvingStatus.published) revert CarvingAlreadyPublished();
        if (_carvings[carvingId].status != CarvingStatus.created) revert CarvingNotFound();
        gallery.push(carvingId);
        _carvings[carvingId].status = CarvingStatus.published;
        emit CarvingPublicized(carvingId);
    }

    /**
     * @notice                  Removes a carving from the public gallery.
     * @param carvingId         The unique ID of the carving to be removed from the gallery.
     */
    function hide(bytes32 carvingId) public onlyOfficiant {
        if (_carvings[carvingId].status != CarvingStatus.published) revert CarvingNotInGallery();
        for (uint256 i = 0; i < gallery.length; i++) {
            if (gallery[i] == carvingId) {
                gallery[i] = gallery[gallery.length - 1];
                gallery.pop();
                _carvings[carvingId].status = CarvingStatus.created;
                emit CarvingHidden(carvingId);
                return;
            }
        }
        revert CarvingNotFound();
    }

    /// PUBLIC METHODS
    /**
     * @notice              Retrieves the ids of carvings in the public gallery.
     * @return galleryIds   The unique IDs of the carvings in the gallery.
     */
    function peruse() external view returns (bytes32[] memory galleryIds) {
        return gallery;
    }

    /**
     * @notice              Retrieves a carving by its unique ID.
     * @param carvingId     The unique ID of the carving.
     * @return to           Who the carving is for.
     * @return from         Who the carving is from.
     * @return message      The message to be carved.
     * @return properties   Metadata for the carving (e.g., display styles).
     */
    function read(bytes32 carvingId) external view returns (string memory to, string memory from, string memory message, bytes31 properties) {
        if (_carvings[carvingId].status == CarvingStatus.free) revert CarvingNotFound();
        Carving memory carving = _carvings[carvingId];
        return (carving.to, carving.from, carving.message, carving.properties);
    }
}
