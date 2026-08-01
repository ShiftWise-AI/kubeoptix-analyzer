"""Seção de referências do relatório de assessment."""

REFERENCES_MD = """\
## Referências utilizadas

1. Kubernetes — *Resource Management for Pods and Containers*  
   https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/

2. Kubernetes — *Assign Memory Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/

3. Kubernetes — *Assign CPU Resources to Containers and Pods*  
   https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/

4. Kubernetes — *Horizontal Pod Autoscaling*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

5. Kubernetes — *HorizontalPodAutoscaler Walkthrough*  
   https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/

6. OpenShift — *Quotas and Limit Ranges*  
   https://docs.openshift.com/container-platform/latest/nodes/clusters/nodes-cluster-limit-ranges.html

7. OpenShift — *Automatically scaling pods with the Horizontal Pod Autoscaler*  
   https://docs.openshift.com/container-platform/latest/nodes/pods/nodes-pods-autoscaling.html

8. CNCF / Kubernetes best practices — *Resource requests and limits* (orientação Burstable / evitar overcommit agressivo)  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

9. Kubernetes — *Pod Quality of Service Classes*  
   https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/

> As sugestões de resources/HPA deste relatório são **heurísticas conservadoras** baseadas nos manifests coletados, não em métricas de uso em tempo real (Prometheus/VPA). Validar em homologação antes de aplicar em produção.
"""
