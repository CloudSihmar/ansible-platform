from sqlalchemy import text
from core.database import engine

def upgrade():
    # Add auth_type column to kubernetes_clusters table
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE kubernetes_clusters 
            ADD COLUMN auth_type VARCHAR(20) DEFAULT 'kubeconfig'
        """))
        conn.execute(text("""
            ALTER TABLE kubernetes_clusters 
            ADD COLUMN description TEXT
        """))
        conn.commit()

def downgrade():
    # Remove the columns if needed
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE kubernetes_clusters 
            DROP COLUMN auth_type
        """))
        conn.execute(text("""
            ALTER TABLE kubernetes_clusters 
            DROP COLUMN description
        """))
        conn.commit()

if __name__ == "__main__":
    upgrade()
    print("✅ Added auth_type and description columns to kubernetes_clusters table")
