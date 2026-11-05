variable "kube_context" {
  type        = string
  description = "Kubernetes context to use for the deployment"
}

variable "kubeconfig_path" {
  type        = string
  description = "Kubernetes config path to use for the deployment"
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
}
