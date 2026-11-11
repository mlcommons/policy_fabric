/* Example issuers for the Simulate tab: preview data, not the registry.

   They stand in for the contract's issuer registry, so a credential type whose trusted list is empty on the
   Simulate tab is trusted from every issuer here that signs it, as the registry decides on the contract.
   Every type a wallet may present (the catalog's "presentable") needs at least one issuer here; the composer's
   browser test checks that, and that nothing here signs a type only components produce. */
const EXAMPLE_ISSUERS = [
  { id: "did:example:registry", name: "Example Registry", types: ["TeamCredential", "ProjectOwnershipCredential", "AffiliationCredential", "EthicsCommitteeAccreditationCredential", "LocationCredential", "LegalDesignationCredential", "ProjectMembershipCredential", "EmailCredential"] },
  { id: "did:example:dac", name: "Data Access Committee", types: ["IRBApprovalCredential", "IntendedDataUseCredential", "AgreementCredential", "ScopedAgreementCredential"] },
  { id: "did:example:platform", name: "Wallet Platform", types: ["publicKeyCredential", "UserPlatformCredential", "WalletVerifyingKeyCredential", "EmailCredential"] },
  { id: "did:example:research-office", name: "University Research Office", types: ["IRBClearanceCredential", "ProjectMembershipCredential"] },
  { id: "did:example:hospital-irb", name: "City Hospital IRB", types: ["IRBApprovalCredential", "IRBClearanceCredential"] },
  { id: "did:example:scripts", name: "Script Registry", types: ["ScriptHashCredential", "ScriptOwnershipCredential"] },
  { id: "did:example:compute", name: "Compute Provider", types: ["ComputeEnvironmentCredential"] }
];
