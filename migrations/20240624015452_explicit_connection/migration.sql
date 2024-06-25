/*
  Warnings:

  - You are about to drop the `_PrismaGachaItemToPrismaGachaPlayer` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "_PrismaGachaItemToPrismaGachaPlayer" DROP CONSTRAINT "_PrismaGachaItemToPrismaGachaPlayer_A_fkey";

-- DropForeignKey
ALTER TABLE "_PrismaGachaItemToPrismaGachaPlayer" DROP CONSTRAINT "_PrismaGachaItemToPrismaGachaPlayer_B_fkey";

-- DropTable
DROP TABLE "_PrismaGachaItemToPrismaGachaPlayer";

-- CreateTable
CREATE TABLE "thiagachaitemtoplayer" (
    "id" SERIAL NOT NULL,
    "item_id" INTEGER NOT NULL,
    "player_id" INTEGER NOT NULL,

    CONSTRAINT "thiagachaitemtoplayer_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "thiagachaitemtoplayer" ADD CONSTRAINT "thiagachaitemtoplayer_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "thiagachaitems"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "thiagachaitemtoplayer" ADD CONSTRAINT "thiagachaitemtoplayer_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "thiagachaplayers"("id") ON DELETE CASCADE ON UPDATE CASCADE;
