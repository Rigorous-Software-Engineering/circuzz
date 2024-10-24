
# ----------------------------------
# General Version Settings
# ----------------------------------

GO_VERSION="1.23.2"
RUST_VERSION="1.81.0"

# ----------------------------------
# List of base images (DO NOT USE DIRECTLY)
# ----------------------------------

IMAGE_BASE=circuzz/base
IMAGE_CIRCOM_BASE=circuzz/circom-base
IMAGE_CORSET_BASE=circuzz/corset-base
IMAGE_GNARK_BASE=circuzz/gnark-base
IMAGE_NOIR_BASE=circuzz/noir-base

# ----------------------------------
# List of available images
# ----------------------------------

IMAGE_CIRCOM_2eaaa6d=circuzz/circom-2eaaa6d # 2eaaa6dface934356972b34cab64b25d382e59de, Wed Apr 24 13:23:35 2024 +0200
IMAGE_CIRCOM_9f3da35=circuzz/circom-9f3da35 # 9f3da35a8ac3107190f8c85c8cf3ea1a0f8780a4, Wed Jul  3 19:50:10 2024 +0200
IMAGE_CIRCOM_570911a=circuzz/circom-570911a # 570911a57afb3459b211921a9c6c699a9e9f5463, Thu Aug 22 11:03:47 2024 +0200
IMAGE_CIRCOM_9a4215b=circuzz/circom-9a4215b # 9a4215bce3ed9d138dae2352f625b04ea4a5b95c, Thu Aug 22 11:15:04 2024 +0200
IMAGE_CIRCOM_b1f795d=circuzz/circom-b1f795d # b1f795d95bb2b9610b99c794597f4f6b41a02640, Thu Aug 22 11:28:51 2024 +0200
IMAGE_CIRCOM_c133004=circuzz/circom-c133004 # c1330049833b5fdbe1c2fb64f9dd04d0f4e112cc, Thu Sep 19 14:56:06 2024 +0100
IMAGE_CIRCOM_f97b7ca=circuzz/circom-f97b7ca # f97b7cad87f23b5dc8d234a4af0795296a8406b9, Wed Sep 25 18:28:56 2024 +0200

IMAGE_CORSET_3145e74=circuzz/corset-3145e74 # 3145e74758fb3d8d71dd5dd45c76bd47fc8a6fa6, Thu Jul 18 16:21:27 2024 +1200
IMAGE_CORSET_dd7a010=circuzz/corset-dd7a010 # dd7a01019b7b997a75587ad0e8a50a7106c98e9c, Fri Jul 19 14:40:17 2024 +1200
IMAGE_CORSET_3e60e39=circuzz/corset-3e60e39 # 3e60e393cc45a070f0d00d22f0193f6e4e6707a2, Mon Jul 22 14:03:35 2024 +1200
IMAGE_CORSET_e50d554=circuzz/corset-e50d554 # e50d554234ceac2ffc7ea24d643ef3eeb8a74ee2, Tue Jul 23 15:30:22 2024 +1200
IMAGE_CORSET_fcd3035=circuzz/corset-fcd3035 # fcd303564977c35a6471db1c3d4b0a369653d496, Thu Jul 25 12:02:07 2024 +1200
IMAGE_CORSET_3fe818e=circuzz/corset-3fe818e # 3fe818eb4b820dbb7133904a126da8301e44ab3e, Thu Oct  3 12:15:23 2024 +0100
# -- no bug newest version --
IMAGE_CORSET_0f6fb5d=circuzz/corset-0f6fb5d # 0f6fb5d309deddb10e25135f36ee5e65d3ebc3d6, Fri Oct  4 00:30:04 2024 +1300

IMAGE_GNARK_e3f932b=circuzz/gnark-e3f932b # e3f932b6cff57f850795d8fef5e51c0176f9d8e2, Thu Jul 11 17:40:57 2024 +0800
IMAGE_GNARK_111a078=circuzz/gnark-111a078 # 111a0789161e18acfab932eed280a120577acae6, Thu Jul 11 11:41:45 2024 +0200
IMAGE_GNARK_d6d85d4=circuzz/gnark-d6d85d4 # d6d85d44699b50f38bcd6acf295fc2cade4b8b61, Thu Jul 25 19:12:49 2024 +0200
IMAGE_GNARK_70baf16=circuzz/gnark-70baf16 # 70baf16c1b70a93c453637f4ac4fd4cc8c9aac62, Fri Jul 26 09:26:12 2024 -0500
IMAGE_GNARK_aa6efa4=circuzz/gnark-aa6efa4 # aa6efa4476d56c026d73ed98f53f80fa00eaabd9, Mon Jul 29 10:45:50 2024 -0400
IMAGE_GNARK_d8ccab5=circuzz/gnark-d8ccab5 # d8ccab5994e0f44b6d62df8ec72e589fb1f4fa5a, Wed Jul 31 09:20:23 2024 -0500
IMAGE_GNARK_ea53f37=circuzz/gnark-ea53f37 # ea53f373f45d2f9ad9cc1639c34359a35f771191, Fri Aug  2 07:22:15 2024 -0500
# -- no bug newest version --
IMAGE_GNARK_3a0fa0f=circuzz/gnark-3a0fa0f # 3a0fa0f316437854d56bf10a1e75811df9697f46, Sat Sep 14 11:15:59 2024 -0500

IMAGE_NOIR_281ebf2_0_41_0=circuzz/noir-281ebf2-bb-0.41.0   # 281ebf26e4cd16daf361938de505697f8d5fbd5e, Fri May 24 16:44:32 2024 +0200
IMAGE_NOIR_9db206e_0_41_0=circuzz/noir-9db206e-bb-0.41.0   # 9db206e98555ccd8089256144ef39ed43bd981b6, Fri May 24 18:03:43 2024 +0200
IMAGE_NOIR_79f8954_44b4be6=circuzz/noir-79f8954-bb-44b4be6 # 79f895490632a8751cc1ce6e05a862e28810cc3f, Tue Oct  1 08:14:38 2024 -0400 | 44b4be6b3aca918d0bc17ff64b701137e308743e, Tue Oct 8 19:58:01 2024 +0300
IMAGE_NOIR_79f8954_6e36f45=circuzz/noir-79f8954-bb-6e36f45 # 79f895490632a8751cc1ce6e05a862e28810cc3f, Tue Oct  1 08:14:38 2024 -0400 | 6e36f45c7d61b4c4507a326b458eb03ec6a1fc0b, Tue Oct 8 20:04:38 2024 -0400
IMAGE_NOIR_1a2ca46_0_56_0=circuzz/noir-1a2ca46-bb-0.56.0   # 1a2ca46af0d1c05813dbe28670a2bc39b79e4c9f, Mon Oct  7 18:58:11 2024 +0100
IMAGE_NOIR_c4273a0_0_56_0=circuzz/noir-c4273a0-bb-0.56.0   # c4273a0c8f8b751a3dbe097e070e4e7b2c8ec438, Mon Oct  7 15:11:12 2024 -0300

# ----------------------------------
# Link the default / newest images
# ----------------------------------

IMAGE_CIRCOM_DEFAULT=$IMAGE_CIRCOM_f97b7ca
IMAGE_CORSET_DEFAULT=$IMAGE_CORSET_0f6fb5d
IMAGE_GNARK_DEFAULT=$IMAGE_GNARK_3a0fa0f
IMAGE_NOIR_DEFAULT=$IMAGE_NOIR_c4273a0_0_56_0