certutil -generateSSTFromWU roots.sst
Import-Certificate -FilePath roots.sst -CertStoreLocation Cert:\LocalMachine\Root