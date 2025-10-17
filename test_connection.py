import asyncio
import asyncpg

DB_CONFIG = {
    "host": "db.vnfqxgvpqulcyvporwem.supabase.co",
    "database": "postgres",
    "user": "postgres",
    "password": "DOMMATI@2025",
    "port": 5432,
}

async def test_listener():
    print("🔗 Tentando conectar ao banco...")
    conn = await asyncpg.connect(**DB_CONFIG)
    print("✅ Conexão com o banco Supabase bem-sucedida!")
    print("👂 Ouvindo canal 'estoque_changes'... (rode NOTIFY no Supabase para testar)")

    async def callback(conn, pid, channel, payload):
        print(f"📢 Notificação recebida!\n Canal: {channel}\n PID: {pid}\n Payload: {payload}")

    await conn.add_listener("estoque_changes", callback)

    try:
        while True:
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        print("\n⏹ Listener interrompido.")
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_listener())
