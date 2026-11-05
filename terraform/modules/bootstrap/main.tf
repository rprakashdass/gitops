locals {
  config_values = {
    configs = {
      cm   = yamldecode(file(var.cm_file)).data
      rbac = yamldecode(file(var.rbac_cm_file)).data
    }
  }

  resource_values = {
    for component, r in var.resources : component => { resources = r }
  }

  secret_extra = yamldecode(file(var.secret_file)).stringData
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  namespace        = var.namespace
  version          = var.chart_version
  create_namespace = true

  values = [
    file(var.values_file),
    yamlencode(local.config_values),
    yamlencode(local.resource_values),
  ]

  set {
    name  = "global.domain"
    value = var.domain
  }
  set {
    name  = "server.ingress.enabled"
    value = tostring(var.ingress_enabled)
  }
  set {
    name  = "server.ingress.ingressClassName"
    value = var.ingress_class_name
  }

  dynamic "set_sensitive" {
    for_each = local.secret_extra
    content {
      name  = "configs.secret.extra.${replace(set_sensitive.key, ".", "\\.")}"
      value = set_sensitive.value
    }
  }
}