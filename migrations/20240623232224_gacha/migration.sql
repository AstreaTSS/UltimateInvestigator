-- CreateEnum
CREATE TYPE "Rarity" AS ENUM ('COMMON', 'UNCOMMON', 'RARE', 'SUPER_RARE', 'LEGENDARY');

-- DropIndex
DROP INDEX "idx_uinewtruthb_name_37580d";

-- AlterTable
ALTER TABLE "thianames" ADD COLUMN     "plural_currency_name" TEXT NOT NULL DEFAULT 'Coins',
ADD COLUMN     "singular_currency_name" TEXT NOT NULL DEFAULT 'Coin';

-- CreateTable
CREATE TABLE "thiagachaitems" (
    "id" SERIAL NOT NULL,
    "guild_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "image" TEXT,
    "rarity" "Rarity" NOT NULL DEFAULT 'COMMON',
    "amount" INTEGER NOT NULL DEFAULT -1,

    CONSTRAINT "thiagachaitems_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "thiagachaplayers" (
    "id" SERIAL NOT NULL,
    "guild_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "currency_amount" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "thiagachaplayers_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "thiagachaconfig" (
    "guild_id" BIGINT NOT NULL,
    "enabled" BOOLEAN NOT NULL DEFAULT false,
    "currency_cost" INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT "thiagachaconfig_pkey" PRIMARY KEY ("guild_id")
);

-- CreateTable
CREATE TABLE "_PrismaGachaItemToPrismaGachaPlayer" (
    "A" INTEGER NOT NULL,
    "B" INTEGER NOT NULL
);

-- CreateIndex
CREATE INDEX "thiagachaitems_guild_id_idx" ON "thiagachaitems"("guild_id");

-- CreateIndex
CREATE INDEX "thiagachaitems_name_idx" ON "thiagachaitems"("name");

-- CreateIndex
CREATE INDEX "thiagachaitems_rarity_idx" ON "thiagachaitems"("rarity");

-- CreateIndex
CREATE INDEX "thiagachaplayers_guild_id_idx" ON "thiagachaplayers"("guild_id");

-- CreateIndex
CREATE INDEX "thiagachaplayers_guild_id_user_id_idx" ON "thiagachaplayers"("guild_id", "user_id");

-- CreateIndex
CREATE UNIQUE INDEX "_PrismaGachaItemToPrismaGachaPlayer_AB_unique" ON "_PrismaGachaItemToPrismaGachaPlayer"("A", "B");

-- CreateIndex
CREATE INDEX "_PrismaGachaItemToPrismaGachaPlayer_B_index" ON "_PrismaGachaItemToPrismaGachaPlayer"("B");

-- CreateIndex
CREATE INDEX "thiatruthbullets_channel_id_idx" ON "thiatruthbullets"("channel_id");

-- CreateIndex
CREATE INDEX "thiatruthbullets_guild_id_idx" ON "thiatruthbullets"("guild_id");

-- CreateIndex
CREATE INDEX "thiatruthbullets_found_idx" ON "thiatruthbullets"("found");

-- AddForeignKey
ALTER TABLE "thiagachaitems" ADD CONSTRAINT "thiagachaitems_guild_id_fkey" FOREIGN KEY ("guild_id") REFERENCES "thiagachaconfig"("guild_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "thiagachaplayers" ADD CONSTRAINT "thiagachaplayers_guild_id_fkey" FOREIGN KEY ("guild_id") REFERENCES "thiagachaconfig"("guild_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "thiagachaconfig" ADD CONSTRAINT "thiagachaconfig_guild_id_fkey" FOREIGN KEY ("guild_id") REFERENCES "thiaguildconfig"("guild_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_PrismaGachaItemToPrismaGachaPlayer" ADD CONSTRAINT "_PrismaGachaItemToPrismaGachaPlayer_A_fkey" FOREIGN KEY ("A") REFERENCES "thiagachaitems"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_PrismaGachaItemToPrismaGachaPlayer" ADD CONSTRAINT "_PrismaGachaItemToPrismaGachaPlayer_B_fkey" FOREIGN KEY ("B") REFERENCES "thiagachaplayers"("id") ON DELETE CASCADE ON UPDATE CASCADE;
