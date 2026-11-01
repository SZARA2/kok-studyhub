import zipfile,os,sys
out=sys.argv[1];z=zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)
for p in sys.argv[2:]:
  for r,d,fs in os.walk(p) if os.path.isdir(p) else [(os.path.dirname(p) or '.',[],[os.path.basename(p)])]:
    for f in fs:
      fp=os.path.join(r,f)
      if '__pycache__' in fp or fp.endswith('.zip'):continue
      z.write(fp,os.path.normpath(fp))
z.close();print(out,len(z.namelist()))
