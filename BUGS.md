# Summary

| tool    | reported | confirmed | fixed |
|---------|----------|-----------|-------|
| circom  | 5        | 5         | 4     |
| corset  | 4        | 4         | 4     |
| gnark   | 4        | 4         | 4     |
| noir    | 3        | 3         | 3     |

Overall, we have 15 bugs that are already **fixed** and only 1 bug that is only **confirmed**. 

---

# Bugs

## Circom

### Bitwise Complement Operator
#### Bug
  * Issue:  https://github.com/iden3/circom/issues/270
  * Commit: 2eaaa6dface934356972b34cab64b25d382e59de
#### Fix
  * No PR (directly pushed to master)
  * Commit: 9f3da35a8ac3107190f8c85c8cf3ea1a0f8780a4

### Different Results for Bitwise Complement Operator with Zero
#### Bug
  * Issue:  https://github.com/iden3/circom/issues/283
  * Commit: 9a4215bce3ed9d138dae2352f625b04ea4a5b95c
#### Fix
  * No PR (directly pushed to master)
  * Commit: b1f795d95bb2b9610b99c794597f4f6b41a02640

### Inconsistent Bitwise Evaluation for Field Prime
#### Bug
  * Issue:  https://github.com/iden3/circom/issues/288
  * Commit: 9f3da35a8ac3107190f8c85c8cf3ea1a0f8780a4
#### Fix
  * No PR (directly pushed to master)
  * Commit: 570911a57afb3459b211921a9c6c699a9e9f5463

### Inconsistent Bitwise Evaluation of small Field Primes
#### Bug
  * Issue:  https://github.com/iden3/circom/issues/298
  * Commit: c1330049833b5fdbe1c2fb64f9dd04d0f4e112cc
#### Fix
  * No PR (directly pushed to master)
  * Commit: f97b7cad87f23b5dc8d234a4af0795296a8406b9

### Polynomial is not Divisible
#### Bug
  * Issue:  https://github.com/iden3/circom/issues/269
  * Commit: latest
### Fix
  * No PR
  * No Fix Commit


## Corset

### Different Behavior for Expansion and Native Flags
#### Bug
  * Issue:  https://github.com/Consensys/corset/issues/219
  * Commit: 3145e74758fb3d8d71dd5dd45c76bd47fc8a6fa6
#### Fix
  * PR:     https://github.com/Consensys/corset/pull/228
  * Commit: dd7a01019b7b997a75587ad0e8a50a7106c98e9c

### Wrong Evaluation of Constraint Expressions using Expansion
#### Bug
  * Issue:  https://github.com/Consensys/corset/issues/241
  * Commit: 3e60e393cc45a070f0d00d22f0193f6e4e6707a2
#### Fix:
  * Issue:  https://github.com/Consensys/corset/pull/242
  * Commit: e50d554234ceac2ffc7ea24d643ef3eeb8a74ee2

### Rework ifs transform (and re-opened issue)
#### Bug
  * Issue:  https://github.com/Consensys/corset/issues/241 , https://github.com/Consensys/corset/issues/243
  * Commit: e50d554234ceac2ffc7ea24d643ef3eeb8a74ee2
#### Fix:
  * Issue:  https://github.com/Consensys/corset/pull/245
  * Commit: fcd303564977c35a6471db1c3d4b0a369653d496

### Wrong evaluation of Normalized Loobean
#### Bug
  * Issue:  https://github.com/Consensys/corset/issues/244
  * Commit: fcd303564977c35a6471db1c3d4b0a369653d496
#### Fix
  * PR:     https://github.com/Consensys/corset/pull/262
  * Commit: 3fe818eb4b820dbb7133904a126da8301e44ab3e


## Gnark

### Or Computation for Constant and Non-Constant
#### Bug
  * No Issue (reported via message)
  * Commit:
    - e3f932b6cff57f850795d8fef5e51c0176f9d8e2
#### Fix
  * PR:
    - https://github.com/Consensys/gnark/pull/1181
  * Commit:
    - 111a0789161e18acfab932eed280a120577acae6

### Wrong Computation of AssertIsLessOrEqual
#### Bug
  * Issue:
    - https://github.com/Consensys/gnark/issues/1227
  * Commit:
    - d6d85d44699b50f38bcd6acf295fc2cade4b8b61
#### Fix
  * PR:
    - https://github.com/Consensys/gnark/pull/1228
  * Commit:
    - 70baf16c1b70a93c453637f4ac4fd4cc8c9aac62

### Minimum 1 Bit for Constant Binary Decomposition
#### Bug
  * No Issue (reported via email)
  * Commit: aa6efa4476d56c026d73ed98f53f80fa00eaabd9
#### Fix
  * PR:     https://github.com/Consensys/gnark/pull/1229
  * Commit: d8ccab5994e0f44b6d62df8ec72e589fb1f4fa5a

### Branch with Unchecked Cast could panic at Compile Time
#### Bug
  * No Issue (reported via email)
  * Commit: d8ccab5994e0f44b6d62df8ec72e589fb1f4fa5a
#### Fix
  * PR:     https://github.com/Consensys/gnark/pull/1234
  * Commit: ea53f373f45d2f9ad9cc1639c34359a35f771191


## Noir

### Wrong Computation of Assertion
#### Bug
  * Issue:  https://github.com/noir-lang/noir/issues/5463
  * Commit: 281ebf26e4cd16daf361938de505697f8d5fbd5e
#### Fix
  * PR:     https://github.com/noir-lang/noir/pull/5100
  * Commit: 9db206e98555ccd8089256144ef39ed43bd981b6

### BB Prover Error in MemBn254CrsFactory
#### Bug
  * Issue BB:    https://github.com/AztecProtocol/aztec-packages/issues/8745
  * Issue Noir:  https://github.com/noir-lang/noir/issues/6147
  * Commit BB:   44b4be6b3aca918d0bc17ff64b701137e308743e
  * Commit Noir: 79f895490632a8751cc1ce6e05a862e28810cc3f
#### Fix
  * PR: https://github.com/AztecProtocol/aztec-packages/pull/9046
  * Commit BB:   6e36f45c7d61b4c4507a326b458eb03ec6a1fc0b
  * Commit Noir: 79f895490632a8751cc1ce6e05a862e28810cc3f

### Stack Overflow for "lt" with Medium Expression Depth
#### Bug
  * Issue:  https://github.com/noir-lang/noir/issues/6150
  * Commit: 1a2ca46af0d1c05813dbe28670a2bc39b79e4c9f
#### Fix
  * PR:     https://github.com/noir-lang/noir/pull/6180
  * Commit: c4273a0c8f8b751a3dbe097e070e4e7b2c8ec438