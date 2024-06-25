-- AlterTable
ALTER TABLE "thiabulletconfig" RENAME CONSTRAINT "uinewconfig_pkey" TO "thiabulletconfig_pkey";

-- AlterTable
ALTER TABLE "thianames" RENAME CONSTRAINT "uinames_pkey" TO "thianames_pkey";

-- AlterTable
ALTER TABLE "thiatruthbullets" RENAME CONSTRAINT "uinewtruthbullets_pkey" TO "thiatruthbullets_pkey";

-- RenameForeignKey
ALTER TABLE "thiabulletconfig" RENAME CONSTRAINT "uinewconfig_names_id_fkey" TO "thiabulletconfig_names_id_fkey";

-- RenameIndex
ALTER INDEX "uinewconfig_names_id_key" RENAME TO "thiabulletconfig_names_id_key";
