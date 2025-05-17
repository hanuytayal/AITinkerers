---
Title: Playbook - Resolving Out Of Memory (OOM) Issues by Restarting the Service

Last updated: 2024-06-18  
Author: IT Operations

---

## Overview
This playbook provides step-by-step instructions for on-call engineers to resolve Out Of Memory (OOM) issues by identifying and restarting the affected service.

---

## Prerequisites

- You have SSH or remote console access to the affected server.
- You have sudo or appropriate permissions to restart services.
- This playbook applies only to services where a restart is safe and authorized. Contact the application owner if unsure.

---

## Step 1: Identify the OOM Event

1. **Check monitoring/alerts**: Review the alert details (e.g., PagerDuty, Datadog, New Relic) to determine which host and service/process was killed by the OOM.
2. **Confirm OOM in system logs**:
   ```
   sudo dmesg | grep -i 'killed process'
   ```
   or
   ```
   grep -i 'oom' /var/log/messages
   ```
   Look for lines similar to:
   ```
   Out of memory: Kill process 12345 (service-name) score XYZ or sacrifice child
   Killed process 12345 (service-name), UID=XXX, total-vm=XXXXkB, anon-rss=XXXXkB, file-rss=XXXXkB, shmem-rss=XXXXkB
   ```

---

## Step 2: Locate the Service

1. From the OOM log entry, note the **process ID (PID)** and **process/service name** (e.g., `service-name`).
2. Determine if the service is managed by a service manager (e.g., `systemd`, `upstart`, `supervisord`, or a custom script).

---

## Step 3: Restart the Service

### For systemd-managed services

1. List the running services to confirm the status:
   ```
   sudo systemctl status <service-name>
   ```
2. If service is inactive (killed), start or restart:
   ```
   sudo systemctl restart <service-name>
   ```
3. Check the status after restart:
   ```
   sudo systemctl status <service-name>
   ```

### For init.d/upstart-managed services

1. Check status:
   ```
   sudo service <service-name> status
   ```
2. Restart the service:
   ```
   sudo service <service-name> restart
   ```

### For supervisor-managed services

1. Check status:
   ```
   sudo supervisorctl status <service-name>
   ```
2. Restart:
   ```
   sudo supervisorctl restart <service-name>
   ```

---

## Step 4: Verify Recovery

1. **Check logs:**  
   ```
   tail -n 50 /var/log/<service-name>/<logfile>.log
   ```
2. **Check the service status** (using above status commands).
3. **Check monitoring dashboards** to ensure resource usage returns to normal and functionality is restored.

---

## Step 5: Document the Incident

- Record the following in the incident tracking system (e.g., Jira, PagerDuty note):
    - Affected host/service.
    - When and how OOM was detected.
    - Any correlated system resource spikes.
    - What actions you took (log excerpts, commands).
    - Service outcome after restart.

---

## Step 6: Escalate if Issue Persists

- If the service continues to experience OOM:
    - Escalate to the application owner or next-level support.
    - Attach all relevant log excerpts and resource usage info.
    - Consider adjusting memory limits or investigating leaks (out of scope for this playbook).

---

## References

- [Detecting OOM Events (Red Hat Documentation)](https://access.redhat.com/solutions/18834)
- [systemd service management](https://www.freedesktop.org/software/systemd/man/systemctl.html)

---

## Appendix

- For containerized services (e.g., Docker, Kubernetes), use container management tools (`docker restart`, `kubectl rollout restart`, etc.) and see respective runbooks.

---