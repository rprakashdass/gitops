module "bootstrap" {
  source       = "../../modules/bootstrap"
  values_file  = "${path.root}/../../../bootstrap/argocd-values.yaml"
  cm_file      = "${path.root}/../../../argocd/rbac/argocd-cm.yaml"
  rbac_cm_file = "${path.root}/../../../argocd/rbac/argocd-rbac-cm.yaml"
  secret_file  = "${path.root}/../../../argocd/rbac/argocd-secret.yaml"

  domain             = var.domain
  ingress_enabled    = var.ingress_enabled
  ingress_class_name = var.ingress_class_name
  resources          = var.resources
}
