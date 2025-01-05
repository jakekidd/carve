// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import "forge-std/Test.sol";
import "../src/Tree.sol";
import "./utils/TestRelayer.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

contract TestTree is Test {
    Tree tree;
    TestRelayer relayer;
    // Our 'officiant' that creates the contract and produces signatures to simulate relayer activity.
    // Private key exclusively used for unit tests.
    address officiant;
    uint256 officiantPrivateKey = 0x2f994cfe918405258483ae1a03d46d1289968c0e022fdbac9a5e7044f8cc8ea9;

    function setUp() public {
        tree = new Tree();
        relayer = new TestRelayer();
        officiant = vm.addr(officiantPrivateKey);
        tree.appoint(officiant);
    }

    /// HELPERS
    // Helper function to sign a carving action.
    function helper_sign(bytes32 carvingId, string memory message) internal view returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, message));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(officiantPrivateKey, ethSignedMessageHash);
        return abi.encodePacked(r, s, v);
    }

    /// OFFICIANT MUTEX METHODS
    // Test for successful appointing of a new officiant.
    function test_Tree__appoint_shouldSucceedWhenCalledByExistingOfficiant() public {
        address newOfficiant = address(0x456);
        tree.appoint(newOfficiant);
        assertTrue(tree.officiants(newOfficiant));
    }

    // Test for successful removal of an officiant.
    function test_Tree__dismiss_shouldSucceedWhenCalledByExistingOfficiant() public {
        address newOfficiant = address(0x456);
        tree.appoint(newOfficiant);
        tree.dismiss(newOfficiant);
        assertFalse(tree.officiants(newOfficiant));
    }

    // Test for failing dismissal of oneself.
    function test_Tree__dismiss_shouldFailWhenTryingToDismissSelf() public {
        vm.expectRevert(Tree.CannotDismissSelf.selector);
        vm.prank(officiant);
        tree.dismiss(officiant);
    }

    /// LIFECYCLE METHODS
    // Test for successful carving via relayer.
    function test_Tree__carve_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving1"));
        string memory message = "Hello, world!";
        bytes memory signature = helper_sign(carvingId, message);

        relayer.relayCarve(address(tree), carvingId, message, signature);
        assertEq(tree.read(carvingId), message);
    }

    // Test for carving with no signature by an officiant.
    function test_Tree__carve_shouldSucceedWithoutSignatureWhenCalledByOfficiant() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving2"));
        string memory message = "Officiant carve.";

        vm.prank(officiant);
        tree.carve(carvingId, message, "");
        assertEq(tree.read(carvingId), message);
    }

    // Test for successful scratch via relayer.
    function test_Tree__scratch_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving5"));
        string memory message = "To be removed.";
        bytes memory carveSignature = helper_sign(carvingId, message);
        bytes memory scratchSignature = helper_sign(carvingId, "");

        relayer.relayCarve(address(tree), carvingId, message, carveSignature);
        relayer.relayScratch(address(tree), carvingId, scratchSignature);

        vm.expectRevert(Tree.CarvingNotFound.selector);
        tree.read(carvingId);
    }

    /// PUBLIC METHODS
    // Test for peruse function to ensure only publicized carvings are shown in the gallery.
    function test_Tree__peruse_shouldOnlyShowPublicizedCarvings() public {
        bytes32 carvingId1 = keccak256(abi.encodePacked("carving7"));
        bytes32 carvingId2 = keccak256(abi.encodePacked("carving8"));
        string memory message1 = "Public carving.";
        string memory message2 = "Private carving.";

        tree.carve(carvingId1, message1, helper_sign(carvingId1, message1));
        tree.carve(carvingId2, message2, helper_sign(carvingId2, message2));

        vm.prank(officiant);
        tree.publicize(carvingId1);

        bytes32[] memory gallery = tree.peruse();
        assertEq(gallery.length, 1);
        assertEq(gallery[0], carvingId1);
    }

    // Test for read function to ensure carvings are correctly retrieved.
    function test_Tree__read_shouldReturnCorrectMessage() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving9"));
        string memory message = "Reading test.";
        bytes memory signature = helper_sign(carvingId, message);

        relayer.relayCarve(address(tree), carvingId, message, signature);
        assertEq(tree.read(carvingId), message);
    }
}
