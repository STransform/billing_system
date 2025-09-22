from django.core.management.base import BaseCommand
from openstack import connection
from core.models import Instance, Volume, FloatingIP, Router, Snapshot, Image

class Command(BaseCommand):
    help = "Sync OpenStack resources into Django DB"

    def handle(self, *args, **kwargs):
        conn = connection.from_config(cloud_name="kolla-admin")

        # ========== INSTANCES ==========
        for s in conn.compute.servers(all_projects=True):
            Instance.objects.update_or_create(
                instance_id=s.id,
                defaults={
                    "tenant_id": s.project_id,
                    "name": s.name,
                    "flavor_id": s.flavor['id'] if isinstance(s.flavor, dict) else s.flavor.get('original_name', ''),
                    "start_date": s.created_at,
                },
            )

        # ========== VOLUMES ==========
        volume_types = {vt.name: vt.id for vt in conn.block_storage.types()}
        for v in conn.block_storage.volumes(details=True, all_projects=True):
            Volume.objects.update_or_create(
                volume_id=v.id,
                defaults={
                    "tenant_id": v.project_id,
                    "volume_name": v.name,
                    "volume_type_id": volume_types.get(v.volume_type, None),
                    "space_allocation_gb": v.size,
                    "start_date": v.created_at,
                },
            )

        # ========== FLOATING IPS ==========
        for f in conn.network.ips(all_projects=True):
            FloatingIP.objects.update_or_create(
                fip_id=f.id,
                defaults={
                    "tenant_id": f.project_id,
                    "ip": f.floating_ip_address,
                    "start_date": f.created_at,
                },
            )

        # ========== ROUTERS ==========
        for r in conn.network.routers():
            if not r.external_gateway_info:
                continue
            Router.objects.update_or_create(
                router_id=r.id,
                defaults={
                    "tenant_id": r.project_id,
                    "name": r.name,
                    "start_date": r.created_at,
                },
            )

        # ========== SNAPSHOTS ==========
        for s in conn.block_storage.snapshots(details=True, all_projects=True):
            Snapshot.objects.update_or_create(
                snapshot_id=s.id,
                defaults={
                    "tenant_id": s.project_id,
                    "name": s.name,
                    "space_allocation_gb": s.size,
                    "start_date": s.created_at,
                },
            )

        # ========== IMAGES ==========
        for i in conn.image.images():
            Image.objects.update_or_create(
                image_id=i.id,
                defaults={
                    "tenant_id": i.owner_id,
                    "name": i.name,
                    "space_allocation_gb": (i.size or 0) / 1024 / 1024 / 1024,
                    "start_date": i.created_at,
                },
            )

        self.stdout.write(self.style.SUCCESS("✅ Cloud resources synced successfully!"))
