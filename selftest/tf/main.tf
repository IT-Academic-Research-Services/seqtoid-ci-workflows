# Minimal valid Terraform config so the reusable terraform-ci.yml has something to fmt + validate
# during the SSOT's own self-test. Not deployed; init runs with -backend=false.
terraform {
  required_version = ">= 1.0"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

resource "null_resource" "selftest" {}
