/*
  Warnings:
  - The primary key for the `thianames` table will be changed. If it partially fails, the table could be left without primary key constraint.

*/
-- DropForeignKey
ALTER TABLE "thiaguildconfig" DROP CONSTRAINT "thiaguildconfig_names_id_fkey";

-- DropIndex
DROP INDEX "thiaguildconfig_names_id_key";

-- AlterTable
ALTER TABLE "thiabulletconfig" ALTER COLUMN "guild_id" DROP DEFAULT;
DROP SEQUENCE "uinewconfig_guild_id_seq";

ALTER TABLE "thianames" RENAME "id" TO "guild_id";

-- AlterTable
ALTER TABLE "thianames" DROP CONSTRAINT "thianames_pkey",
ALTER COLUMN "guild_id" DROP DEFAULT,
ALTER COLUMN "guild_id" SET DATA TYPE BIGINT,
ADD CONSTRAINT "thianames_pkey" PRIMARY KEY ("guild_id");
DROP SEQUENCE "PrismaNames_id_seq";

-- InsertTable
UPDATE thianames SET guild_id = g.guild_id FROM thiaguildconfig g WHERE thianames.guild_id = g.names_id;

-- AlterTable
ALTER TABLE "thiaguildconfig" DROP COLUMN "names_id";

-- RenameForeignKey
ALTER TABLE "thiaguildconfig" RENAME CONSTRAINT "thiaguildconfig_guild_id_fkey" TO "thiaguildconfig_guild_id_bullets_fkey";

-- AddForeignKey
ALTER TABLE "thiaguildconfig" ADD CONSTRAINT "thiaguildconfig_guild_id_names_fkey" FOREIGN KEY ("guild_id") REFERENCES "thianames"("guild_id") ON DELETE CASCADE ON UPDATE CASCADE;
