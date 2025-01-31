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
    address officiant;
    uint256 officiantPrivateKey = 0x2f994cfe918405258483ae1a03d46d1289968c0e022fdbac9a5e7044f8cc8ea9;

    function setUp() public {
        tree = new Tree();
        relayer = new TestRelayer();
        officiant = vm.addr(officiantPrivateKey);
        tree.appoint(officiant);
    }

    /// HELPERS
    function helper_signCarve(bytes32 carvingId, bytes32 properties, string memory message) internal view returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, properties, message));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(officiantPrivateKey, ethSignedMessageHash);
        return abi.encodePacked(r, s, v);
    }

    function helper_signGallery(bytes32 carvingId, uint256 nonce) internal view returns (bytes memory) {
        bytes32 messageHash = keccak256(abi.encodePacked(carvingId, nonce));
        bytes32 ethSignedMessageHash = MessageHashUtils.toEthSignedMessageHash(messageHash);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(officiantPrivateKey, ethSignedMessageHash);
        return abi.encodePacked(r, s, v);
    }

    /// OFFICIANT METHODS
    function test_Tree__appoint_shouldSucceedWhenCalledByExistingOfficiant() public {
        address newOfficiant = address(0x456);
        tree.appoint(newOfficiant);
        assertTrue(tree.officiants(newOfficiant));
    }

    function test_Tree__dismiss_shouldSucceedWhenCalledByExistingOfficiant() public {
        address newOfficiant = address(0x456);
        tree.appoint(newOfficiant);
        tree.dismiss(newOfficiant);
        assertFalse(tree.officiants(newOfficiant));
    }

    function test_Tree__dismiss_shouldFailWhenTryingToDismissSelf() public {
        vm.expectRevert(Tree.CannotDismissSelf.selector);
        vm.prank(officiant);
        tree.dismiss(officiant);
    }

    /// LIFECYCLE METHODS
    function test_Tree__carve_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving1"));
        bytes32 properties = keccak256(abi.encodePacked("style1"));
        string memory message = "Hello, world!";
        bytes memory signature = helper_signCarve(carvingId, properties, message);

        relayer.relayCarve(address(tree), carvingId, properties, message, signature);
        (bytes32 returnedProperties, string memory returnedMessage) = tree.read(carvingId);
        assertEq(returnedProperties, properties);
        assertEq(returnedMessage, message);
    }

    function test_Tree__carve_shouldSucceedWithoutSignatureWhenCalledByOfficiant() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving2"));
        bytes32 properties = keccak256(abi.encodePacked("style2"));
        string memory message = "Officiant carve.";

        vm.prank(officiant);
        tree.carve(carvingId, properties, message, "");
        (bytes32 returnedProperties, string memory returnedMessage) = tree.read(carvingId);
        assertEq(returnedProperties, properties);
        assertEq(returnedMessage, message);
    }

    function test_Tree__scratch_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving5"));
        bytes32 properties = keccak256(abi.encodePacked("style5"));
        string memory message = "To be removed.";
        bytes memory carveSignature = helper_signCarve(carvingId, properties, message);
        bytes memory scratchSignature = helper_signCarve(carvingId, properties, "");

        relayer.relayCarve(address(tree), carvingId, properties, message, carveSignature);
        relayer.relayScratch(address(tree), carvingId, properties, scratchSignature);

        vm.expectRevert(Tree.CarvingNotFound.selector);
        tree.read(carvingId);
    }

    /// GALLERY METHODS
    function test_Tree__publicize_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving7"));
        bytes32 properties = keccak256(abi.encodePacked("style7"));
        string memory message = "Public carving.";
        bytes memory carveSignature = helper_signCarve(carvingId, properties, message);
        relayer.relayCarve(address(tree), carvingId, properties, message, carveSignature);

        uint256 nonce = tree.galleryNonces(carvingId);
        bytes memory gallerySignature = helper_signGallery(carvingId, nonce);
        vm.prank(officiant);
        tree.publicize(carvingId, gallerySignature);

        bytes32[] memory gallery = tree.peruse();
        assertEq(gallery.length, 1);
        assertEq(gallery[0], carvingId);
    }

    function test_Tree__hide_shouldSucceedWhenCalledByRelayer() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving8"));
        bytes32 properties = keccak256(abi.encodePacked("style8"));
        string memory message = "Hidden carving.";
        bytes memory carveSignature = helper_signCarve(carvingId, properties, message);
        relayer.relayCarve(address(tree), carvingId, properties, message, carveSignature);

        uint256 nonce = tree.galleryNonces(carvingId);
        bytes memory publicizeSignature = helper_signGallery(carvingId, nonce);
        vm.prank(officiant);
        tree.publicize(carvingId, publicizeSignature);

        nonce = tree.galleryNonces(carvingId);
        bytes memory hideSignature = helper_signGallery(carvingId, nonce);
        vm.prank(officiant);
        tree.hide(carvingId, hideSignature);

        bytes32[] memory gallery = tree.peruse();
        assertEq(gallery.length, 0);
    }

    /// PUBLIC METHODS
    function test_Tree__read_shouldReturnCorrectPropertiesAndMessage() public {
        bytes32 carvingId = keccak256(abi.encodePacked("carving9"));
        bytes32 properties = keccak256(abi.encodePacked("style9"));
        string memory message = "Reading test.";
        bytes memory signature = helper_signCarve(carvingId, properties, message);

        relayer.relayCarve(address(tree), carvingId, properties, message, signature);
        (bytes32 returnedProperties, string memory returnedMessage) = tree.read(carvingId);
        assertEq(returnedProperties, properties);
        assertEq(returnedMessage, message);
    }
}
