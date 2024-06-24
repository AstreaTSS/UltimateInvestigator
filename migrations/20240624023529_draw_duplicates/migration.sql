-- DropIndex
DROP INDEX "thiagachaitems_rarity_idx";

-- AlterTable
ALTER TABLE "thiagachaconfig" ADD COLUMN     "draw_duplicates" BOOLEAN NOT NULL DEFAULT true;

-- CreateIndex
CREATE INDEX "thiagachaitems_amount_idx" ON "thiagachaitems"("amount");
