variable "namespace" {
  type        = string
  description = "Namespace for argocd"
  default     = "argocd"
}

variable "chart_version" {
  type        = string
  description = "Chart version for argocd"
  default     = "10.11.6"
}

variable "values_file" {
  type        = string
  description = "Helm chart values file for argocd"
}

variable "cm_file" {
  type        = string
  description = "argocd-cm ConfigMap manifest; its data becomes configs.cm"
}

variable "secret_file" {
  type        = string
  description = "argocd-secret manifest; its stringData becomes configs.secret.extra"
}

variable "rbac_cm_file" {
  type        = string
  description = "argocd-rbac-cm ConfigMap manifest; its data becomes configs.rbac"
}

variable "domain" {
  type        = string
  description = "Domain for argocd ingress"
}

variable "ingress_enabled" {
  type        = bool
  description = "Enable ingress for argocd"
  default     = true
}

variable "ingress_class_name" {
  type        = string
  description = "Ingress class name for argocd ingress"
}

variable "resources" {
  type = map(object({
    requests = map(string)
    limits   = map(string)
  }))
  description = "Resource requests and limits for argocd components"
  default     = {}

  validation {
    condition     = alltrue([for k in keys(var.resources) : contains(["server", "controller", "repoServer", "redis", "applicationSet"], k)])
    error_message = "resources keys must be among: server, controller, repoServer, redis, applicationSet."
  }
}
