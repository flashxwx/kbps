upload-to-server:
	rsync -avz --update --exclude-from='exclude.txt' \
	./ admin@192.168.1.212:/home/admin/Desktop/Kbps

upload-dotenv-to-server:
	scp .env \
	admin@192.168.1.212:/home/admin/Desktop/Kbps/.env

download-peaks-db:
	sqlite3_rsync admin@192.168.1.212:/home/admin/Desktop/Kbps/database/slay_peaks.sqlite.db /home/flash/Desktop/Slay.one/Kbps-3.0/database/slay_peaks.sqlite.db

download-ranking-db:
	sqlite3_rsync admin@192.168.1.212:/home/admin/Desktop/Kbps/database/slay_ranking.sqlite.db /home/flash/Desktop/Slay.one/Kbps-3.0/database/slay_ranking.sqlite.db

download-log:
	scp \
	admin@192.168.1.212:/home/admin/Desktop/Kbps/*.log \
	./

database-backup:
	sqlite3_rsync -v admin@192.168.1.212:/home/admin/Desktop/Kbps/database/users.sqlite.db database/.backup/users.sqlite.db
	sqlite3_rsync -v admin@192.168.1.212:/home/admin/Desktop/Kbps/database/slay_peaks.sqlite.db database/.backup/slay_peaks.sqlite.db
	sqlite3_rsync -v admin@192.168.1.212:/home/admin/Desktop/Kbps/database/slay_replay.sqlite.db database/.backup/slay_replay.sqlite.db
	sqlite3_rsync -v admin@192.168.1.212:/home/admin/Desktop/Kbps/database/slay_ranking.sqlite.db database/.backup/slay_ranking.sqlite.db

	scp \
	admin@192.168.1.212:/home/admin/Desktop/Kbps/database/*.db.txt \
	./database/.backup