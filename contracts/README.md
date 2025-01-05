# Carve: Contracts

This repository contains the smart contracts for the Carve protocol, an on-chain inscription storage system designed for secure, efficient, and privacy-preserving message storage. The primary contract is **Tree**, which manages message inscriptions ("carvings") and public gallery submissions.

## Features

- **Inscription Storage**: Store messages on-chain with unique IDs.
- **Public Gallery**: Optionally add carvings to a public gallery.
- **Officiant Access Control**: Carvings are managed by 'officiants' (role-based permissions).
- **Relayer Compatibility**: Supports off-chain systems to initiate transactions on behalf of users. Prevents replay attacks with signature tracking.

### Interface

The **Tree** contract handles lifecycle operations like creating, removing, and publicizing carvings. It includes:

- **`carve`**: Stores a new carving.
- **`scratch`**: Removes a carving.
- **`publicize`**: Adds a carving to the public gallery.
- **`hide`**: Removes a carving from the gallery.
- **`read`**: Retrieves a carving by ID.
- **`peruse`**: Returns the list of public carvings.

### Access Control

The deployer is the initial officiant. Officiants can appoint or dismiss other officiants freely from the pool. Anyone with the officiant role can carve or remove inscriptions by calling those methods directly or signing the arguments for execution by a relayer.

Officiants can also publicize and hide specific carvings by ID. This will likely be a submission-governed process in the future, handled externally off-chain. Note that regardless of publication, all carvings are visible, however the private identity of the user who submitted the carving is preserved.

### Relayer Integration

Relayer services can interact with the contract using ECDSA signatures. The contract verifies signatures to ensure only authorized actions are taken. Officiants can also call methods directly without a signature.

## License

This project is licensed under the MIT License.
