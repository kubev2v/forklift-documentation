The following recommendations can improve performance when migrating virtual machines (VMs) from VMware vSphere to OpenShift Virtualization using the Migration Toolkit for Virtualization (MTV).

**These recommendations are not requirements for migration.**

## Use fast, dedicated networks for the migration

Use networks with a minimum transmission speed of 10 GbE in both the VMware and OpenShift Virtualization environments.

Use dedicated networks to ensure that other services are not affected by the migration process.

These recommendations also apply to a network selected as an [ESXi endpoint](#esxi-endpoint).

## Select an appropriate endpoint

The endpoint affects the ESXi data store read rate, which impacts the disk transfer speed and migration duration.

The average read rate for the vSphere endpoint is 800 MBps, while the average read rate for the ESXi endpoint is 300-500 MBps. See [BZ#1957985](https://bugzilla.redhat.com/show_bug.cgi?id=1957985) for details.

Select the endpoint that is appropriate for your vSphere version and number of hosts:

- vSphere 6.5: ESXi endpoint is the only option. [BZ#1973193](https://bugzilla.redhat.com/show_bug.cgi?id=1973193)
- vSphere 6.7:
  - One or two ESXi hosts: vSphere endpoint
  - Three or more ESXi hosts: ESXi endpoint

### About the vSphere endpoint

When you create a VMware provider by using the MTV web console, MTV communicates directly with vSphere to manage the migration. This is referred to as the vSphere endpoint. It is significantly faster than the ESXi endpoint.

Using the vSphere endpoint for migration increases the memory and CPU usage of the vSphere VM.

The vSphere endpoint can support up to 50 concurrent disk migrations from each host.

### About the ESXi endpoint

After you have added ESXi hosts by using the MTV web console, you can select each ESXi host and then select a migration network. The selected network must have access to the OpenShift Virtualization interface. This is referred to as the ESXi endpoint.

## Use VDDK 7.0.2

MTV uses the VMware Virtual Disk Development Kit (VDDK) SDK to copy disks.

VDDK version 7.0.2 is 15% faster than VDDK 6.5 or 6.7 and works with vSphere 6.5 and 6.7.

## Configure the optimal number of concurrent disk transfers

The `MAX_VM_INFLIGHT` parameter determines the maximum number of concurrent VM disk transfers for each ESXi host. The default value is `20`. If `MAX_VM_INFLIGHT` is `20` and there are two ESXi hosts, each host can transfer up to 20 disks during a migration.

Note: Warm migration uses snapshots to copy a VM disk while the VM is running. Then the VM is stopped and migrated during the cutover phase. The disk is included in the total number of disks specified by the `MAX_VM_INFLIGHT` parameter for the entire warm migration, _even when the cutover phase has not yet started_.

The following table describes the optimal `MAX_VM_INFLIGHT` values for vSphere versions and endpoints:

| vSphere version | Endpoint     | Optimal `MAX_VM_INFLIGHT` value | Maximum `MAX_VM_INFLIGHT` value |
| :------------- | :------------- | :-------------: | :-------------: |
| 6.5   | ESXi endpoint  | 10 | 20<sup>1</sup> |
| 6.7   | ESXi endpoint  | 40<sup>2</sup> | 199 |
| 6.7   | vSphere endpoint | 50<sup>3</sup> | 150 |

<sup>1</sup> Exceeding this value can cause the disk transfer process to fail.

<sup>2</sup> Exceeding this value does not improve performance.

<sup>3</sup> Exceeding this value can degrate the performance of both the migration process and vSphere.

To change the `MAX_VM_INFLIGHT` parameter value:

1. In the OpenShift Container Platform web console, click **Workloads > Deployments**.
2. Click the **forklift-controller** project.
3. Click the **Environment** tab.
4. Click **Add more** under **Single values (env)**.
5. Enter `MAX_VM_INFLIGHT` in the **Name** field, enter the value, and then click **Save**.

**Migration example**

- Environment:
  - 50 x 50 GB disks
  - One ESXi host
  - vSphere 6.7
  - vSphere endpoint
  - `MAX_VM_INFLIGHT` = `50`
- Performance:
  - ESXi data store read rate: 800 MBps
  - Migration rate: 914-1,135 MBps

## Add ESXi hosts for large concurrent migrations

You can add ESXi hosts to improve performance if you are migrating large numbers of VMs concurrently.

Ensure that the VMs are evenly distributed among the ESXi hosts that are being used for migration.

The following table displays the maximum recommended number of concurrent VM migrations per host. If you want to migrate a larger number of VMs concurrently, you should consider adding more hosts.

| vSphere version | Endpoint     | Maximum concurrent migrations per host<sup>1</sup> |
| :------------- | :------------- | :-------------: |
| 6.5   | ESXi endpoint  | 10 |
| 6.7   | ESXi endpoint  | 40 |
| 6.7   | vSphere endpoint | 25 |

<sup>1</sup> Exceeding this value does not improve performance.

**Performance examples**

The following table displays the improved performance of migrating 50 VMs with additional ESXi hosts.

| vSphere version | Endpoint   | Number of hosts | Rate | Duration (mm:ss) |
| :------------- | :------------- | :-------------: | :-------------: | :-------------: |
| 6.5   | ESXi endpoint | 3 | 1,051 MBps | 40:34 |
| 6.5   | ESXi endpoint | 5 | 1,282 MBps | 33:16 |
| 6.7   | vSphere endpoint | 1 | 1,135 MBps | 41:43 |
| 6.7   | vSphere endpoint | 2 | 1,578 MBps | 30:24 |
