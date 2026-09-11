USE AbsensiDB;

SELECT 
    a.Id,
    k.NIK,
    k.Nama,
    k.FaceEmbedding,
    a.Tanggal,
    a.JamMasuk,
    a.JamKeluar,
    a.Status,
    a.Keterangan,
    a.CreatedAt
FROM Absensi a 
JOIN Karyawan k ON a.KaryawanId = k.Id
ORDER BY a.Tanggal DESC, a.JamMasuk DESC;