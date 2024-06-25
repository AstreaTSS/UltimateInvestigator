-- DropForeignKey
ALTER TABLE "thiabulletconfig" DROP CONSTRAINT "thiabulletconfig_names_id_fkey";

-- DropIndex
DROP INDEX "thiabulletconfig_names_id_key";

-- CreateTable
CREATE TABLE "thiaguildconfig" (
    "guild_id" BIGINT NOT NULL,
    "player_role" BIGINT,
    "names_id" INTEGER,

    CONSTRAINT "thiaguildconfig_pkey" PRIMARY KEY ("guild_id")
);

-- InsertTable
INSERT INTO "thiaguildconfig" ("guild_id", "player_role", "names_id")
SELECT "guild_id", "player_role", "names_id" FROM "thiabulletconfig";

-- AlterTable
ALTER TABLE "thiabulletconfig" DROP COLUMN "names_id",
DROP COLUMN "player_role";

-- CreateIndex
CREATE UNIQUE INDEX "thiaguildconfig_names_id_key" ON "thiaguildconfig"("names_id");

-- AddForeignKey
ALTER TABLE "thiaguildconfig" ADD CONSTRAINT "thiaguildconfig_names_id_fkey" FOREIGN KEY ("names_id") REFERENCES "thianames"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "thiaguildconfig" ADD CONSTRAINT "thiaguildconfig_guild_id_fkey" FOREIGN KEY ("guild_id") REFERENCES "thiabulletconfig"("guild_id") ON DELETE CASCADE ON UPDATE CASCADE;
