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
    function helper_signCarve(bytes32 carvingId, string memory message) internal view returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, message));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(officiantPrivateKey, ethSignedMessageHash);
        return abi.encodePacked(r, s, v);
    }

    // Helper function to sign a gallery action with nonce.
    function helper_signGallery(bytes32 carvingId, uint256 nonce) internal view returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, nonce));
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
        bytes memory signature = helper_signCarve(carvingId, message);

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
        bytes memory carveSignature = helper_signCarve(carvingId, message);
        bytes memory scratchSignature = helper_signCarve(carvingId, "");

        relayer.relayCarve(address(tree), carvingId, message, carveSignature);
        relayer.relayScratch(address(tree), carvingId, scratchSignature);

        vm.expectRevert(Tree.CarvingNotFound.selector);
        tree.read(carvingId);
    }

    /// GALLERY METHODS
    // Test for successful publicizing of a carving.
    function test_Tree__publicize_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving7"));
        string memory message = "Public carving.";
        bytes memory carveSignature = helper_signCarve(carvingId, message);
        relayer.relayCarve(address(tree), carvingId, message, carveSignature);

        uint256 nonce = tree.galleryNonces(carvingId);
        bytes memory gallerySignature = helper_signGallery(carvingId, nonce);
        vm.prank(officiant);
        tree.publicize(carvingId, gallerySignature);

        bytes32[] memory gallery = tree.peruse();
        assertEq(gallery.length, 1);
        assertEq(gallery[0], carvingId);
    }

    // Test for successful hiding of a carving.
    function test_Tree__hide_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving8"));
        string memory message = "Hidden carving.";
        bytes memory carveSignature = helper_signCarve(carvingId, message);
        relayer.relayCarve(address(tree), carvingId, message, carveSignature);

        // Publicize the carving first
        uint256 nonce = tree.galleryNonces(carvingId);
        bytes memory publicizeSignature = helper_signGallery(carvingId, nonce);
        vm.prank(officiant);
        tree.publicize(carvingId, publicizeSignature);

        // Increment the nonce for the hide action
        nonce = tree.galleryNonces(carvingId);
        bytes memory hideSignature = helper_signGallery(carvingId, nonce);
        vm.prank(officiant);
        tree.hide(carvingId, hideSignature);

        // Verify the gallery is empty after hiding the carving
        bytes32[] memory gallery = tree.peruse();
        assertEq(gallery.length, 0);
    }

    /// PUBLIC METHODS
    // Test for read function to ensure carvings are correctly retrieved.
    function test_Tree__read_shouldReturnCorrectMessage() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving9"));
        string memory message = "Reading test.";
        bytes memory signature = helper_signCarve(carvingId, message);

        relayer.relayCarve(address(tree), carvingId, message, signature);
        assertEq(tree.read(carvingId), message);
    }
}
