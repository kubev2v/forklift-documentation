The following recommendations can improve performance when migrating virtual machines from Red Hat Virtualization (RHV) to OpenShift Virtualization using the Migration Toolkit for Virtualization (MTV).

<!-- https://access.redhat.com/articles/6380311 -->

**These recommendations are not requirements for migration.**

## Use fast, dedicated networks for the migration

- Extend the RHV network to the network of the Openshift Container Platform worker nodes.
- Ensure that networks  in both the RHV and OpenShift Virtualization environments have a minimum transmission speed of 10 GbE.
- Ensure that there are no bottlenecks.
- Use a dedicated network.

  The migration process consumes significant bandwidth on the RHV `ovirtmgmt` network. If other services use the same network, this situation can affect the services and migration speeds.

## Ensure fast read rates from storage domains to hosts

- Storage domain read rates affect the total transfer time. Therefore, it is important to ensure the fastest possible read rate from the RHV storage domains to the hosts.
- The average read rate for a RHV host migrating 10 virtual machines is 1070 MBps.

## Set "MAX_VM_INFLIGHT" to "10"

- Set the `MAX_VM_INFLIGHT` parameter to `10`.

  The `MAX_VM_INFLIGHT` parameter determines the maximum number of concurrent VM disk transfers for each RHV host. The default value is `20`. A value greater than `10` does not result in faster migration speeds.

  The RHV Manager distributes the VM disks randomly among the hosts during migration. Uneven distribution is expected behavior.

To change the `MAX_VM_INFLIGHT` parameter value:

1. In the OpenShift Container Platform web console, click **Workloads > Deployments**.
2. Click the **forklift-controller** project.
3. Click the **Environment** tab.
4. Click **Add more** under **Single values (env)**.
5. Enter `MAX_VM_INFLIGHT` in the **Name** field, enter `10`, and then click **Save**.

## Add RHV hosts

- The RHV Manager selects the hosts randomly for migration ([BZ#1995065](https://bugzilla.redhat.com/show_bug.cgi?id=1995065)). This might cause uneven distribution of VMs among the hosts and place an additional burden on the `ovirtmgmt` network. However, even with random host selection, adding RHV hosts improves performance.
- If you want to use a specific host for migration, ensure that its status is `up` and place the other hosts in `maintenance` mode.

**Performance example**

- 40 virtual machines migrated with different numbers of RHV hosts.
- Adding RHV hosts increases the average read rate from the storage domain.
- Adding RHV hosts reduces the migration time.

Number of RHV hosts  |Read rate  |Migration time (mm:ss)
--|--|--
1 |1,033 MBps  |30:30
4 |1,935 MBps  |22:49
