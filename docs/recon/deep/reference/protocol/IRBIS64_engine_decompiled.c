/* Ghidra pseudo-C of selected IRBIS64.dll engine functions */

/* ===== Irbis_Format @ 400b80cc ===== */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void Irbis_Format(int *param_1,int param_2,int param_3)

{
  int iVar1;
  undefined1 *puVar2;
  undefined4 *puVar3;
  char *pcVar4;
  undefined4 *puVar5;
  undefined4 *in_FS_OFFSET;
  byte bVar6;
  char acStackY_149d [1018];
  undefined2 auStackY_10a3 [1827];
  undefined1 *puVar7;
  undefined *puStack_258;
  undefined1 *puStack_254;
  undefined4 uStack_24c;
  undefined1 *puStack_248;
  undefined1 *puStack_244;
  int local_234;
  undefined *local_230 [4];
  int local_220;
  int local_21c;
  int local_218;
  int local_214;
  undefined1 local_205;
  int local_200;
  int local_1fc;
  undefined4 local_1f4;
  undefined4 local_1f0;
  int local_e8 [2];
  undefined4 local_dd [8];
  char local_bb [4];
  undefined4 uStack_b7;
  char acStack_b3 [23];
  int local_9c;
  undefined4 local_98;
  undefined4 local_94;
  undefined4 *local_90;
  undefined4 local_71 [19];
  int local_24;
  undefined1 local_1d;
  undefined4 local_1c;
  undefined1 local_15;
  int local_14;
  int local_10;
  int *local_c;
  undefined4 local_8;
  
                    /* 0xb80cc  8  Irbis_Format */
  bVar6 = 0;
  puStack_244 = &stack0xfffffffc;
  puVar7 = &stack0xfffffffc;
  puVar2 = &stack0xfffffffc;
  local_230[0] = (undefined *)0x0;
  local_234 = 0;
  local_e8[0] = 0;
  puStack_248 = &LAB_400b8452;
  uStack_24c = *in_FS_OFFSET;
  *in_FS_OFFSET = &uStack_24c;
  local_214 = param_3;
  local_10 = param_2;
  local_c = param_1;
  if (*(int *)((int)param_1 + 0x80a) + -1 < param_2) {
    local_218 = -0x66;
    puStack_244 = &stack0xfffffffc;
  }
  else {
    local_14 = 0;
    DAT_400e31f0 = '\0';
    DAT_400e31ec = '\0';
    DAT_400e31f4 = '\0';
    local_8 = 100000000;
    local_200 = param_3 + -1;
    local_1fc = Irbismaxmfn(param_1);
    local_1fc = local_1fc + -1;
    _DAT_400e71ec = *(undefined4 *)((int)local_c + 0x80e);
    local_24 = 0;
    local_9c = 0;
    acStack_b3[0x13] = '\x01';
    acStack_b3[0x14] = '\0';
    acStack_b3[0x15] = '\0';
    acStack_b3[0x16] = '\0';
    puVar3 = (undefined4 *)&DAT_400b8468;
    puVar5 = local_71;
    for (iVar1 = 4; iVar1 != 0; iVar1 = iVar1 + -1) {
      *puVar5 = *puVar3;
      puVar3 = puVar3 + (uint)bVar6 * -2 + 1;
      puVar5 = puVar5 + (uint)bVar6 * -2 + 1;
    }
    *(undefined2 *)puVar5 = *(undefined2 *)puVar3;
    *(undefined *)((int)puVar5 + (uint)bVar6 * -4 + 2) =
         *(undefined *)((int)puVar3 + (uint)bVar6 * -4 + 2);
    local_1f4 = 0;
    local_1f0 = 0;
    acStack_b3[3] = '\n';
    acStack_b3[4] = '\0';
    acStack_b3[5] = '\0';
    acStack_b3[6] = '\0';
    local_bb[0] = s_ABCDEFGHI<_400b847c[0];
    local_bb[1] = s_ABCDEFGHI<_400b847c[1];
    local_bb[2] = s_ABCDEFGHI<_400b847c[2];
    local_bb[3] = s_ABCDEFGHI<_400b847c[3];
    (&uStack_b7)[(uint)bVar6 * -2] = *(undefined4 *)("\nABCDEFGHI<" + (uint)bVar6 * -8 + 4);
    *(undefined2 *)(acStack_b3 + ((uint)bVar6 * -4 + (uint)bVar6 * -4) * 2) =
         *(undefined2 *)("\nABCDEFGHI<" + (uint)bVar6 * -8 + (uint)bVar6 * -8 + 8);
    (acStack_b3 + ((uint)bVar6 * -4 + (uint)bVar6 * -4) * 2)[((uint)bVar6 * -2 + 1) * 2] =
         ("\nABCDEFGHI<" + (uint)bVar6 * -8 + (uint)bVar6 * -8 + 8)[((uint)bVar6 * -2 + 1) * 2];
    pcVar4 = "!2; 2, 2, 2, 2, 2, 2, 2, 2, 2; 2. ";
    puVar3 = local_dd;
    for (iVar1 = 8; iVar1 != 0; iVar1 = iVar1 + -1) {
      *puVar3 = *(undefined4 *)pcVar4;
      pcVar4 = pcVar4 + ((uint)bVar6 * -2 + 1) * 4;
      puVar3 = puVar3 + (uint)bVar6 * -2 + 1;
    }
    *(undefined2 *)puVar3 = *(undefined2 *)pcVar4;
    acStack_b3[7] = 'P';
    acStack_b3[8] = '\0';
    acStack_b3[9] = '\0';
    acStack_b3[10] = '\0';
    acStack_b3[0xf] = 'L';
    acStack_b3[0x10] = '\0';
    acStack_b3[0x11] = '\0';
    acStack_b3[0x12] = '\0';
    acStack_b3[0xb] = '\x01';
    acStack_b3[0xc] = '\0';
    acStack_b3[0xd] = '\0';
    acStack_b3[0xe] = '\0';
    local_94 = 0;
    local_98 = 10;
    local_90 = FUN_4000a75c(100);
    local_205 = 0;
    local_15 = 0x20;
    local_1d = 0x20;
    local_1c = 0;
    puStack_254 = &LAB_400b826d;
    puStack_258 = (undefined *)*in_FS_OFFSET;
    *in_FS_OFFSET = &puStack_258;
    FUN_400b02c4();
    FUN_400b0830();
    FUN_400b7470('\0',*(undefined4 *)(*(int *)(*local_c + 0x2c) + 4 + local_10 * 0x43),puVar7,
                 (int)&stack0xfffffffc);
    *in_FS_OFFSET = puStack_258;
    puStack_254 = (undefined1 *)0x400b827d;
    FUN_400b1388();
    *(undefined1 *)(*(int *)((int)local_c + 0x80e) + local_9c) = 0;
    if ((DAT_400e31f8 == '\0') && (DAT_400e31f4 == '\0')) {
      puStack_254 = (undefined1 *)0x400b82ba;
      puVar2 = &stack0xfffffffc;
      FUN_400b77b8((int *)((int)local_c + 0x80e),(int *)((int)local_c + 0x81a));
    }
    puStack_254 = (undefined1 *)0x400b82d2;
    FUN_400b74cc((int *)((int)local_c + 0x80e),(int *)((int)local_c + 0x81a),puVar2,
                 (int)&stack0xfffffffc);
    DAT_400e7228 = FUN_4000b37c(*(char **)((int)local_c + 0x80e),"&&&&&");
    if (DAT_400e7228 == (char *)0x0) {
      DAT_400e7228 = *(char **)((int)local_c + 0x80e);
    }
    if (DAT_400e31ec != '\0') {
      FUN_40088428(DAT_400e7228);
      DAT_400e31ec = '\0';
    }
    if (DAT_400e31f0 != '\0') {
      FUN_40088588(DAT_400e7228);
      DAT_400e31f0 = '\0';
    }
    if (DAT_400e31f4 != '\0') {
      FUN_40088790(DAT_400e7228);
      DAT_400e31f4 = '\0';
    }
    local_218 = local_14;
    if (local_14 == 0x39) {
      puStack_254 = (undefined1 *)0x400b837b;
      FUN_4000aa6c(DAT_400e71d8,&local_234);
      puStack_254 = (undefined1 *)local_234;
      puStack_258 = &DAT_400b84e4;
      FUN_400042c8((int *)local_230,3);
      FUN_40023740(local_230[0],local_e8);
      local_21c = FUN_40004208(local_e8[0]);
      if (0 < local_9c) {
        local_9c = local_9c + -1;
      }
      if (0 < local_21c) {
        local_24 = 1;
        local_220 = local_21c;
        do {
          FUN_400b0108((int)local_c,local_9c,*(undefined1 *)(local_e8[0] + -1 + local_24),
                       (int)&stack0xfffffffc);
          local_9c = local_9c + 1;
          local_24 = local_24 + 1;
          local_220 = local_220 + -1;
        } while (local_220 != 0);
      }
      FUN_400b0108((int)local_c,local_9c,0,(int)&stack0xfffffffc);
    }
    FUN_400029b0((int)local_90);
  }
  *in_FS_OFFSET = puStack_258;
  puStack_254 = (undefined1 *)0x400b8446;
  FUN_40003f9c(&local_234,2);
  puStack_254 = (undefined1 *)0x400b8451;
  FUN_40003f78(local_e8);
  return;
}



/* ===== UNIFOR @ 4009fbf0 ===== */
// decompile failed: Exception while decompiling 4009fbf0: process: timeout


/* ===== Irbis_InitPFT @ 400b00cc ===== */

undefined4 Irbis_InitPFT(int param_1,char *param_2)

{
  undefined4 uVar1;
  
                    /* 0xb00cc  9  Irbis_InitPFT */
  uVar1 = FUN_400af858(param_1,param_2);
  return uVar1;
}



/* ===== IrbisFindPosting @ 400cb498 ===== */

uint IrbisFindPosting(int param_1,char *param_2,uint *param_3)

{
  int iVar1;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined4 extraout_ECX_01;
  undefined4 extraout_ECX_02;
  undefined4 extraout_ECX_03;
  LONG extraout_EDX;
  LONG extraout_EDX_00;
  undefined4 extraout_EDX_01;
  undefined4 *in_FS_OFFSET;
  undefined4 uStack_160;
  undefined1 *puStack_15c;
  undefined1 *puStack_158;
  char local_144 [256];
  int local_44;
  int local_40;
  int local_3c;
  int local_38;
  uint local_34;
  int local_30;
  uint local_2c;
  int local_28;
  uint local_20;
  uint local_1c;
  int local_18;
  uint local_14;
  uint *local_10;
  char *local_c;
  int local_8;
  
                    /* 0xcb498  14  IrbisFindPosting */
  puStack_158 = &stack0xfffffffc;
  puStack_15c = &LAB_400cb713;
  uStack_160 = *in_FS_OFFSET;
  *in_FS_OFFSET = &uStack_160;
  local_10 = param_3;
  local_c = param_2;
  local_8 = param_1;
  FUN_4000b1a8(local_144,param_2);
  local_18 = FUN_400c9a80(local_8,local_144,0);
  if (local_18 == 0) {
    if ((*(int *)(local_8 + 0x5b1) < 1) || (10 < *(int *)(local_8 + 0x5b1))) {
      local_40 = *(int *)(local_8 + 0x584);
      *(undefined4 *)(local_8 + 0x5b1) = 0;
    }
    else {
      local_40 = *(int *)(local_8 + 0x584 + *(int *)(local_8 + 0x5b1) * 4);
    }
    local_44 = local_40;
    iVar1 = FUN_40028978(*(int *)(local_40 + 0x1048),
                         *(int *)(*(int *)(local_40 + 0x1048) + 0xc) + -1);
    local_38 = *(int *)((iVar1 + -1) * 0xc + local_44 + 0x81a);
    iVar1 = FUN_40028978(*(int *)(local_44 + 0x1048),
                         *(int *)(*(int *)(local_44 + 0x1048) + 0xc) + -1);
    local_3c = *(int *)((iVar1 + -1) * 0xc + local_44 + 0x81e);
    local_2c = FUN_40026c7c(local_3c,local_38,extraout_ECX);
    local_28 = extraout_EDX;
    FUN_40026be0((HANDLE)(int)*(short *)(local_44 + 4),0,extraout_ECX_00,local_2c,extraout_EDX);
    FUN_40026c20((HANDLE)(int)*(short *)(local_44 + 4),(LPVOID)(local_44 + 0x100c),0x14);
    FUN_40023da0((u_long *)(local_44 + 0x100c),8);
    if (*(int *)(local_44 + 0x1014) < 1) {
      *in_FS_OFFSET = uStack_160;
      return local_14;
    }
    local_34 = local_2c;
    local_30 = local_28;
    if (*(int *)(local_44 + 0x1010) == -0x3e9) {
      local_20 = FUN_400caf48(local_8,&local_2c,local_10,&local_1c);
    }
    else {
      while ((local_3c != -1 &&
             (local_20 = FUN_400cac04(local_8,local_10,&local_1c,local_2c,local_28),
             (int)local_20 < 0))) {
        local_2c = FUN_40026c7c(*(int *)(local_44 + 0x1010),*(int *)(local_44 + 0x100c),
                                extraout_ECX_01);
        local_3c = *(int *)(local_44 + 0x1010);
        if (local_3c == -1) break;
        local_28 = extraout_EDX_00;
        FUN_40026be0((HANDLE)(int)*(short *)(local_44 + 4),0,extraout_ECX_02,local_2c,
                     extraout_EDX_00);
        FUN_40026c20((HANDLE)(int)*(short *)(local_44 + 4),(LPVOID)(local_44 + 0x100c),0x14);
        FUN_40023da0((u_long *)(local_44 + 0x100c),8);
      }
    }
    local_14 = local_20;
    iVar1 = FUN_40024bb4(local_10,(uint *)(local_44 + 0x1020));
    if (0 < iVar1) {
      local_14 = Irbisnxtpost(local_8,extraout_EDX_01,extraout_ECX_03);
    }
  }
  *in_FS_OFFSET = uStack_160;
  return local_14;
}



/* ===== Irbisfind @ 400c9ae4 ===== */

int Irbisfind(int param_1,char *param_2)

{
  int iVar1;
  undefined4 extraout_ECX;
  int local_14;
  
                    /* 0xc9ae4  19  Irbisfind */
  for (local_14 = FUN_4000b140(param_2); (0 < local_14 && ((byte)param_2[local_14 + -1] < 0x21));
      local_14 = local_14 + -1) {
    param_2[local_14 + -1] = '\0';
  }
  FUN_400bfc0c(param_1,param_2);
  iVar1 = FUN_400c94a0(param_1,param_2,CONCAT31((int3)((uint)extraout_ECX >> 8),1));
  return iVar1;
}



/* ===== IrbisSearch_Range @ 400be07c ===== */

void IrbisSearch_Range(int *param_1,int *param_2,undefined4 param_3,int param_4,int param_5)

{
  int iVar1;
  int *piVar2;
  undefined4 uVar3;
  int *piVar4;
  int *piVar5;
  int iVar6;
  int *piVar7;
  int iVar8;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined4 extraout_ECX_01;
  undefined4 extraout_ECX_02;
  undefined4 extraout_ECX_03;
  undefined4 extraout_ECX_04;
  undefined4 uVar9;
  undefined4 extraout_ECX_05;
  int unaff_EBX;
  int *in_FS_OFFSET;
  uint *local_d4;
  undefined *local_d0;
  char *local_cc;
  undefined4 local_c8;
  char *local_c4;
  int local_c0;
  char *local_bc;
  int local_b8;
  char *local_b4;
  int local_b0;
  char *local_ac;
  int local_a8;
  undefined4 local_a4 [8];
  int local_84;
  int local_80;
  int local_7c;
  int local_78;
  int local_74;
  int *local_64;
  int local_60;
  int *local_5c;
  int *local_58;
  int *local_54;
  int *local_50;
  int *local_4c;
  int *local_48;
  int *local_44;
  int *local_40;
  int iVar10;
  int iVar11;
  undefined1 *puVar12;
  int *piVar13;
  uint3 in_stack_fffffff0;
  uint uVar14;
  char cVar15;
  byte bVar16;
  
                    /* 0xbe07c  72  IrbisSearch_Range */
  iVar8 = 0x19;
  do {
    iVar8 = iVar8 + -1;
  } while (iVar8 != 0);
  LOCK();
  UNLOCK();
  uVar14 = (uint)in_stack_fffffff0;
  puVar12 = &LAB_400beccc;
  iVar11 = *in_FS_OFFSET;
  *in_FS_OFFSET = (int)&stack0xffffffdc;
  FUN_40028a28(param_4);
  iVar1 = (**(code **)(*param_2 + 0x14))();
  if (iVar1 == 0) goto LAB_400beca6;
  if (6 < (byte)(uVar14 >> 0x18)) {
    uVar14 = CONCAT13(6,(int3)uVar14);
  }
  piVar2 = (int *)FUN_400031c8((int *)PTR_PTR_40011464,'\x01',extraout_ECX);
  iVar1 = (**(code **)(*param_2 + 0x14))();
  if (-1 < iVar1 + -1) {
    unaff_EBX = 0;
    local_74 = iVar1;
    do {
      (**(code **)(*param_2 + 0xc))(param_2,unaff_EBX,local_a4);
      piVar2 = (int *)0x400be114;
      uVar9 = local_a4[0];
      uVar3 = (**(code **)(*param_2 + 0x18))(param_2,unaff_EBX);
      (**(code **)(*piVar2 + 0x38))(piVar2,uVar9,uVar3);
      unaff_EBX = unaff_EBX + 1;
      local_74 = local_74 + -1;
    } while (local_74 != 0);
  }
  iVar10 = -1;
  local_60 = -1;
  local_64 = (int *)0xffffffff;
  piVar4 = FUN_4005aa68((int *)PTR_DAT_4005aa10,'\x01',param_5);
  piVar5 = FUN_4005aa68((int *)PTR_DAT_4005aa10,'\x01',param_5);
  local_40 = FUN_400288a8((int *)PTR_DAT_4002812c,'\x01',extraout_ECX_00);
  iVar1 = 0;
  iVar6 = (**(code **)(*piVar2 + 0x14))();
  if (-1 < iVar6 + -1) {
    unaff_EBX = 0;
    local_74 = iVar6;
    do {
      (**(code **)(*piVar2 + 0xc))(piVar2,unaff_EBX,&local_a8);
      iVar6 = FUN_40004208(local_a8);
      if ((0 < iVar6) &&
         ((**(code **)(*piVar2 + 0xc))(piVar2,unaff_EBX,&local_ac), *local_ac == '#')) {
        if (2 < (byte)(uVar14 >> 0x18)) {
          uVar14 = CONCAT13(2,(int3)uVar14);
        }
        iVar6 = (**(code **)(*piVar2 + 0x18))(piVar2,unaff_EBX);
        if (iVar6 == 0) {
          (**(code **)(*piVar2 + 0x44))(piVar2,unaff_EBX);
        }
        else {
          iVar1 = iVar1 + 1;
          piVar13 = (int *)(**(code **)(*piVar2 + 0x18))(piVar2,unaff_EBX);
          iVar6 = FUN_40003388(piVar13,(int)PTR_DAT_4002812c);
          FUN_400bd3a8(iVar6,(int)piVar5);
          cVar15 = (char)(uVar14 >> 0x18);
          if (cVar15 == '\0') {
            FUN_400bd0f0((int)piVar4,(int)piVar5);
          }
          else if (cVar15 == '\x01') {
            if ((iVar10 == -1) || (piVar5[3] < iVar10)) {
              iVar10 = piVar5[3];
            }
            if (iVar1 == 1) {
              FUN_400bd0f0((int)piVar4,(int)piVar5);
            }
            else {
              FUN_400bd1bc((int)piVar4,(int)piVar5);
            }
            FUN_400bd2f0((int)piVar4,(int)local_40);
            if (local_40[3] == 0) {
              FUN_4005af28((int)piVar4,0);
              break;
            }
          }
          else if (cVar15 == '\x02') {
            if (unaff_EBX == 0) {
              iVar10 = piVar5[3];
            }
            else {
              (**(code **)(*piVar2 + 0xc))(piVar2,0,&local_b0);
              iVar6 = FUN_40004208(local_b0);
              if ((iVar6 < 1) ||
                 ((**(code **)(*piVar2 + 0xc))(piVar2,0,&local_b4), *local_b4 == '#')) {
                FUN_400bd264((int)piVar4,(int)piVar5);
                goto LAB_400be302;
              }
            }
            FUN_400bd0f0((int)piVar4,(int)piVar5);
          }
LAB_400be302:
          (**(code **)(*piVar2 + 0x24))(piVar2,unaff_EBX,0);
        }
      }
      unaff_EBX = unaff_EBX + 1;
      local_74 = local_74 + -1;
    } while (local_74 != 0);
  }
  if (((0 < iVar1) && (0 < piVar4[3])) &&
     (FUN_400bd2f0((int)piVar4,(int)local_40), local_40[3] == 0)) {
    FUN_4005af28((int)piVar4,0);
  }
  iVar6 = (**(code **)(*piVar2 + 0x14))();
  if (((iVar6 == iVar1) || (iVar10 == 0)) ||
     ((0 < iVar1 && (((char)(uVar14 >> 0x18) == '\x01' && (piVar4[3] == 0)))))) {
LAB_400be3b9:
    FUN_400bd2f0((int)piVar4,param_4);
  }
  else {
    (**(code **)(*piVar2 + 0xc))(piVar2,0,&local_b8);
    iVar1 = FUN_40004208(local_b8);
    uVar9 = extraout_ECX_01;
    if ((0 < iVar1) &&
       ((((**(code **)(*piVar2 + 0xc))(piVar2,0,&local_bc), uVar9 = extraout_ECX_02,
         *local_bc == '#' && ((char)(uVar14 >> 0x18) == '\x02')) && (piVar4[3] == 0))))
    goto LAB_400be3b9;
    if (param_1 != (int *)0x0) {
      local_50 = (int *)0x0;
      local_54 = (int *)0x0;
      local_58 = (int *)0x0;
      local_5c = (int *)0x0;
      if (2 < (byte)(uVar14 >> 0x18)) {
        local_44 = FUN_400288a8((int *)PTR_DAT_4002812c,'\x01',uVar9);
        local_50 = FUN_4005aa68((int *)PTR_DAT_4005aa10,'\x01',1000);
        local_54 = FUN_4005aa68((int *)PTR_DAT_4005aa10,'\x01',1000);
        if (3 < (byte)(uVar14 >> 0x18)) {
          local_48 = FUN_400288a8((int *)PTR_DAT_4002812c,'\x01',extraout_ECX_03);
          local_58 = FUN_4005aa68((int *)PTR_DAT_4005aa10,'\x01',0x100);
          local_5c = FUN_4005aa68((int *)PTR_DAT_4005aa10,'\x01',0x100);
        }
        iVar1 = (**(code **)(*piVar2 + 0x14))();
        if (-1 < iVar1 + -1) {
          unaff_EBX = 0;
          uVar9 = extraout_ECX_04;
          local_74 = iVar1;
          do {
            local_4c = FUN_400288a8((int *)PTR_DAT_4002812c,'\x01',uVar9);
            (**(code **)(*piVar2 + 0x24))(piVar2,unaff_EBX,local_4c);
            unaff_EBX = unaff_EBX + 1;
            local_74 = local_74 + -1;
            uVar9 = extraout_ECX_05;
          } while (local_74 != 0);
        }
      }
      iVar1 = (**(code **)(*piVar2 + 0x14))();
      if (-1 < iVar1 + -1) {
        iVar10 = 0;
        local_74 = iVar1;
        do {
          (**(code **)(*piVar2 + 0xc))(piVar2,iVar10,&local_c0);
          iVar1 = FUN_40004208(local_c0);
          piVar13 = piVar5;
          if ((iVar1 < 1) ||
             ((**(code **)(*piVar2 + 0xc))(piVar2,iVar10,&local_c4), piVar13 = piVar5,
             *local_c4 != '#')) {
            FUN_4005af28((int)piVar13,0);
            if (local_50 != (int *)0x0) {
              FUN_4005af28((int)local_50,0);
            }
            if (local_58 != (int *)0x0) {
              FUN_4005af28((int)local_58,0);
            }
            local_40 = local_64;
            local_44 = (int *)0x400be55f;
            iVar1 = local_60;
            piVar5 = local_50;
            piVar4 = local_58;
            (**(code **)(*piVar13 + 0xc))(piVar13,iVar10,&local_c8);
            uVar9 = local_c8;
            FUN_40004140((int *)&local_d0,*(char **)((int)param_1 + 0x7da));
            piVar2 = (int *)0x400be58b;
            FUN_4000afc4(local_d0,(int *)&local_cc);
            iVar6 = FUN_400b9dd8(param_1,local_cc,uVar9,iVar11,(int)puVar12,iVar10,unaff_EBX,iVar8,
                                 uVar14,(int)param_2);
            if (iVar6 == -999) break;
            cVar15 = (char)(uVar14 >> 0x18);
            if (cVar15 == '\0') {
              FUN_400bd0f0((int)piVar4,(int)piVar5);
            }
            else if (cVar15 == '\x02') {
              if (iVar10 == 0) {
                FUN_400bd264((int)piVar5,(int)piVar4);
                FUN_4005b004((int)piVar4,(int)piVar5);
              }
              else {
                FUN_400bd264((int)piVar4,(int)piVar5);
              }
            }
            else {
              if ((iVar1 == 0) && (iVar10 == 0)) {
                FUN_400bd0f0((int)piVar4,(int)piVar5);
                if (local_50 != (int *)0x0) {
                  FUN_400bd0f0((int)local_54,(int)local_50);
                }
                if (local_58 != (int *)0x0) {
                  FUN_400bd0f0((int)local_5c,(int)local_58);
                }
              }
              else {
                FUN_400bd1bc((int)piVar4,(int)piVar5);
                if (local_50 != (int *)0x0) {
                  FUN_400bd1bc((int)local_54,(int)local_50);
                }
                if (local_58 != (int *)0x0) {
                  FUN_400bd1bc((int)local_5c,(int)local_58);
                }
              }
              if ((local_58 != (int *)0x0) &&
                 (FUN_400bd2f0((int)local_5c,(int)local_40), local_40[3] == 0)) {
                FUN_4005af28((int)piVar4,0);
                break;
              }
              if ((local_50 != (int *)0x0) &&
                 (FUN_400bd2f0((int)local_54,(int)local_40), local_40[3] == 0)) {
                FUN_4005af28((int)piVar4,0);
                break;
              }
              FUN_400bd2f0((int)piVar4,(int)local_40);
              if (local_40[3] == 0) {
                FUN_4005af28((int)piVar4,0);
                break;
              }
              if ((local_50 != (int *)0x0) && ((local_60 == -1 || (local_50[3] < local_60)))) {
                local_60 = local_50[3];
              }
              if ((local_58 != (int *)0x0) &&
                 ((local_64 == (int *)0xffffffff || (local_58[3] < (int)local_64)))) {
                local_64 = (int *)local_58[3];
              }
            }
          }
          iVar10 = iVar10 + 1;
          local_74 = local_74 + -1;
        } while (local_74 != 0);
      }
      FUN_400bd2f0((int)piVar4,param_4);
      bVar16 = (byte)(uVar14 >> 0x18);
      if ((0 < *(int *)(param_4 + 0xc)) && (2 < bVar16)) {
        iVar8 = (**(code **)(*piVar2 + 0x14))();
        bVar16 = (byte)(uVar14 >> 0x18);
        if (1 < iVar8) {
          iVar8 = (**(code **)(*piVar2 + 0x14))();
          if (-1 < iVar8 + -1) {
            iVar1 = 0;
            local_74 = iVar8;
            do {
              piVar2 = local_5c;
              piVar4 = (int *)(**(code **)(*local_5c + 0x18))(local_5c,iVar1);
              FUN_40003388(piVar4,(int)PTR_DAT_4002812c);
              piVar4 = (int *)0x400be7a9;
              (**(code **)(*piVar2 + 0xc))(piVar2,iVar1,&local_d4);
              FUN_400bc388(param_1,local_d4,piVar4,iVar11,(int)puVar12,iVar1);
              iVar1 = iVar1 + 1;
              local_74 = local_74 + -1;
            } while (local_74 != 0);
          }
          if (-1 < *(int *)(param_4 + 0xc) + -1) {
            iVar8 = 0;
            local_74 = *(int *)(param_4 + 0xc);
            do {
              FUN_4005af28((int)piVar4,0);
              iVar1 = (**(code **)(*piVar2 + 0x14))();
              if (-1 < iVar1 + -1) {
                piVar13 = (int *)0x0;
                local_78 = iVar1;
                do {
                  FUN_4005af28((int)piVar5,0);
                  piVar5 = piVar13;
                  iVar1 = FUN_40028978(param_4,iVar8);
                  piVar2 = (int *)0x0;
                  iVar6 = 0;
                  piVar4 = (int *)0x0;
                  cVar15 = (char)(uVar14 >> 0x18);
                  local_40 = (int *)0x400be838;
                  piVar13 = piVar5;
                  piVar7 = (int *)(**(code **)(iRam00000000 + 0x18))(0,piVar5);
                  local_40 = (int *)0x400be843;
                  iVar10 = FUN_40003388(piVar7,(int)PTR_DAT_4002812c);
                  local_40 = (int *)0x400be84e;
                  FUN_400bc1bc(iVar10,(int)piVar5,iVar6,cVar15,(int)piVar5,piVar4,iVar6,(int)piVar2,
                               iVar1);
                  if (piVar13 == (int *)0x0) {
                    FUN_400bd0f0((int)piVar4,(int)piVar5);
                  }
                  else {
                    FUN_400bd1bc((int)piVar4,(int)piVar5);
                  }
                  FUN_400bd2f0((int)piVar4,(int)local_44);
                  if (local_44[3] == 0) {
                    FUN_400289b4(param_4,iVar8,0);
                    break;
                  }
                  piVar13 = (int *)((int)piVar13 + 1);
                  local_78 = local_78 + -1;
                } while (local_78 != 0);
              }
              if ((3 < (byte)(uVar14 >> 0x18)) && (0 < local_44[3])) {
                if (-1 < local_44[3] + -1) {
                  iVar11 = 0;
                  local_78 = local_44[3];
                  do {
                    FUN_4005af28((int)piVar4,0);
                    iVar1 = (**(code **)(*piVar2 + 0x14))();
                    if (-1 < iVar1 + -1) {
                      piVar13 = (int *)0x0;
                      local_7c = iVar1;
                      do {
                        FUN_4005af28((int)piVar5,0);
                        iVar1 = FUN_40028978(param_4,iVar8);
                        piVar5 = piVar13;
                        piVar2 = (int *)FUN_40028978((int)local_44,iVar11);
                        iVar6 = 0;
                        piVar4 = (int *)0x0;
                        cVar15 = (char)(uVar14 >> 0x18);
                        local_40 = (int *)0x400be94c;
                        piVar13 = piVar5;
                        piVar7 = (int *)(**(code **)(*piVar2 + 0x18))(piVar2,piVar5);
                        local_40 = (int *)0x400be957;
                        iVar10 = FUN_40003388(piVar7,(int)PTR_DAT_4002812c);
                        local_40 = (int *)0x400be962;
                        FUN_400bc1bc(iVar10,(int)piVar5,iVar6,cVar15,(int)piVar5,piVar4,iVar6,
                                     (int)piVar2,iVar1);
                        if (piVar13 == (int *)0x0) {
                          FUN_400bd0f0((int)piVar4,(int)piVar5);
                        }
                        else {
                          FUN_400bd1bc((int)piVar4,(int)piVar5);
                        }
                        FUN_400bd2f0((int)piVar4,(int)local_48);
                        if (local_48[3] == 0) {
                          FUN_400289b4((int)local_44,iVar11,0);
                          break;
                        }
                        piVar13 = (int *)((int)piVar13 + 1);
                        local_7c = local_7c + -1;
                      } while (local_7c != 0);
                    }
                    if ((4 < (byte)(uVar14 >> 0x18)) && (0 < local_48[3])) {
                      iVar1 = local_48[3];
                      if (-1 < local_48[3] + -1) {
                        do {
                          local_7c = iVar1;
                          FUN_4005af28((int)piVar4,0);
                          iVar1 = (**(code **)(*piVar2 + 0x14))();
                          if (-1 < iVar1 + -1) {
                            piVar13 = (int *)0x0;
                            local_80 = iVar1;
                            do {
                              FUN_4005af28((int)piVar5,0);
                              if ((char)(uVar14 >> 0x18) == '\x05') {
                                iVar10 = FUN_40028978(param_4,iVar8);
                                piVar2 = (int *)FUN_40028978((int)local_44,iVar11);
                                iVar1 = FUN_40028978((int)local_48,iVar10);
                                piVar4 = (int *)0x0;
                                piVar5 = (int *)(**(code **)(*piVar2 + 0x14))();
                                cVar15 = (char)(uVar14 >> 0x18);
                                local_40 = (int *)0x400bea75;
                                piVar7 = (int *)(**(code **)(*piVar2 + 0x18))(piVar2,piVar13);
                                local_40 = (int *)0x400bea80;
                                iVar6 = FUN_40003388(piVar7,(int)PTR_DAT_4002812c);
                                local_40 = (int *)0x400bea8b;
                                FUN_400bc1bc(iVar6,(int)piVar5,iVar1,cVar15,(int)piVar5,piVar4,iVar1
                                             ,(int)piVar2,iVar10);
                              }
                              else {
                                iVar10 = FUN_40028978(param_4,iVar8);
                                piVar2 = (int *)FUN_40028978((int)local_44,iVar11);
                                piVar5 = piVar13;
                                iVar1 = FUN_40028978((int)local_48,iVar10);
                                piVar4 = (int *)0x0;
                                cVar15 = (char)(uVar14 >> 0x18);
                                local_40 = (int *)0x400beac6;
                                piVar13 = piVar5;
                                piVar7 = (int *)(**(code **)(*piVar2 + 0x18))(piVar2,piVar5);
                                local_40 = (int *)0x400bead1;
                                iVar6 = FUN_40003388(piVar7,(int)PTR_DAT_4002812c);
                                local_40 = (int *)0x400beadc;
                                FUN_400bc1bc(iVar6,(int)piVar5,iVar1,cVar15,(int)piVar5,piVar4,iVar1
                                             ,(int)piVar2,iVar10);
                              }
                              if (piVar13 == (int *)0x0) {
                                FUN_400bd0f0((int)piVar4,(int)piVar5);
                              }
                              else {
                                FUN_400bd1bc((int)piVar4,(int)piVar5);
                              }
                              iVar10 = 0x400beb05;
                              FUN_400bd2f0((int)piVar4,(int)local_40);
                              if (local_40[3] == 0) {
                                FUN_400289b4((int)local_48,iVar10,0);
                                break;
                              }
                              if ((iVar1 == -1) ||
                                 (iVar10 = (**(code **)(*piVar2 + 0x14))(),
                                 iVar10 + piVar5[3] < iVar1)) {
                                (**(code **)(*piVar2 + 0x14))();
                              }
                              piVar13 = (int *)((int)piVar13 + 1);
                              local_80 = local_80 + -1;
                            } while (local_80 != 0);
                          }
                          local_7c = local_7c + -1;
                          iVar1 = local_7c;
                        } while (local_7c != 0);
                      }
                      do {
                        iVar1 = FUN_400285d8((int)local_48,0);
                        if (-1 < iVar1) {
                          FUN_40028b94((int)local_48,iVar1);
                        }
                      } while (-1 < iVar1);
                      if (local_48[3] == 0) {
                        FUN_400289b4((int)local_44,iVar11,0);
                      }
                    }
                    iVar11 = iVar11 + 1;
                    local_78 = local_78 + -1;
                  } while (local_78 != 0);
                }
                do {
                  iVar1 = FUN_400285d8((int)local_44,0);
                  if (-1 < iVar1) {
                    FUN_40028b94((int)local_44,iVar1);
                  }
                } while (-1 < iVar1);
                if (local_44[3] == 0) {
                  FUN_400289b4(param_4,iVar8,0);
                }
              }
              iVar8 = iVar8 + 1;
              local_74 = local_74 + -1;
            } while (local_74 != 0);
          }
          do {
            iVar8 = FUN_400285d8(param_4,0);
            if (-1 < iVar8) {
              FUN_40028b94(param_4,iVar8);
            }
            bVar16 = (byte)(uVar14 >> 0x18);
          } while (-1 < iVar8);
        }
      }
      if (2 < bVar16) {
        FUN_400031f8(local_44);
        FUN_4005ab08(local_50);
        FUN_4005ab08(local_54);
        if (3 < bVar16) {
          FUN_400031f8(local_48);
          FUN_4005ab08(local_58);
          FUN_4005ab08(local_5c);
        }
        iVar8 = (**(code **)(*piVar2 + 0x14))();
        if (-1 < iVar8 + -1) {
          iVar1 = 0;
          local_74 = iVar8;
          do {
            piVar13 = (int *)(**(code **)(*piVar2 + 0x18))(piVar2,iVar1);
            piVar13 = (int *)FUN_40003388(piVar13,(int)PTR_DAT_4002812c);
            FUN_400031f8(piVar13);
            iVar1 = iVar1 + 1;
            local_74 = local_74 + -1;
          } while (local_74 != 0);
        }
      }
    }
  }
  FUN_4005ab08(piVar4);
  FUN_4005ab08(piVar5);
  FUN_400031f8(local_40);
  FUN_400031f8(piVar2);
LAB_400beca6:
  *in_FS_OFFSET = iVar11;
  FUN_40003f9c((int *)&local_d4,0xd);
  FUN_40003f78(&local_84);
  return;
}



/* ===== InsertTerm @ 400cc920 ===== */

undefined4 InsertTerm(int param_1,char *param_2,u_long *param_3)

{
  char cVar1;
  int iVar2;
  uint uVar3;
  uint uVar4;
  DWORD DVar5;
  u_long uVar6;
  undefined4 uVar7;
  int iVar8;
  undefined4 extraout_ECX;
  undefined4 extraout_ECX_00;
  undefined4 extraout_ECX_01;
  undefined4 extraout_ECX_02;
  undefined4 extraout_ECX_03;
  undefined4 extraout_ECX_04;
  undefined4 extraout_ECX_05;
  undefined4 extraout_ECX_06;
  undefined4 extraout_ECX_07;
  undefined4 extraout_ECX_08;
  undefined4 extraout_ECX_09;
  undefined4 extraout_ECX_10;
  undefined4 extraout_ECX_11;
  undefined4 extraout_ECX_12;
  undefined4 extraout_ECX_13;
  undefined4 extraout_ECX_14;
  undefined4 extraout_ECX_15;
  undefined4 extraout_ECX_16;
  undefined4 extraout_ECX_17;
  undefined4 extraout_ECX_18;
  undefined4 extraout_ECX_19;
  undefined4 extraout_ECX_20;
  undefined4 extraout_ECX_21;
  undefined4 extraout_ECX_22;
  undefined4 extraout_ECX_23;
  undefined4 extraout_ECX_24;
  undefined4 extraout_ECX_25;
  undefined4 extraout_ECX_26;
  undefined4 extraout_ECX_27;
  undefined4 extraout_ECX_28;
  undefined4 extraout_ECX_29;
  undefined4 extraout_ECX_30;
  undefined4 extraout_ECX_31;
  undefined4 extraout_ECX_32;
  undefined4 extraout_ECX_33;
  undefined4 extraout_ECX_34;
  undefined4 extraout_ECX_35;
  undefined4 extraout_ECX_36;
  undefined4 extraout_ECX_37;
  undefined4 extraout_ECX_38;
  undefined4 extraout_ECX_39;
  undefined4 extraout_ECX_40;
  undefined4 extraout_ECX_41;
  undefined4 extraout_ECX_42;
  undefined4 extraout_ECX_43;
  undefined4 extraout_ECX_44;
  undefined4 extraout_ECX_45;
  undefined4 extraout_ECX_46;
  int extraout_EDX;
  LONG extraout_EDX_00;
  int extraout_EDX_01;
  int extraout_EDX_02;
  LONG extraout_EDX_03;
  int extraout_EDX_04;
  int extraout_EDX_05;
  int extraout_EDX_06;
  int extraout_EDX_07;
  int extraout_EDX_08;
  int extraout_EDX_09;
  int extraout_EDX_10;
  int extraout_EDX_11;
  int extraout_EDX_12;
  int extraout_EDX_13;
  int extraout_EDX_14;
  int extraout_EDX_15;
  uint extraout_EDX_16;
  uint extraout_EDX_17;
  int extraout_EDX_18;
  LONG extraout_EDX_19;
  uint extraout_EDX_20;
  int extraout_EDX_21;
  u_long *puVar9;
  u_long *puVar10;
  undefined4 *in_FS_OFFSET;
  bool bVar11;
  byte bVar12;
  char *pcVar13;
  undefined1 *puStack_125c;
  undefined1 *puStack_1258;
  undefined1 *puStack_1254;
  u_long local_1244 [8];
  u_long local_1224;
  undefined4 local_1220;
  int local_121c;
  int local_1218;
  int local_1214;
  u_long local_1210 [8];
  undefined4 local_11f0;
  undefined4 local_11ec;
  u_long local_11e8 [121];
  int iStack_1004;
  u_long local_9e8 [512];
  u_long local_1e8;
  undefined4 local_1e4;
  int local_1e0;
  int local_1dc;
  int local_1d8;
  char local_1d4 [256];
  int local_d4;
  short *local_d0;
  DWORD local_cc;
  DWORD local_c8;
  uint local_c4;
  int local_c0;
  short *local_b8;
  int local_b4;
  u_long *local_b0;
  uint local_ac;
  int local_a8;
  int local_a4;
  undefined4 local_a0;
  int local_9c;
  int local_98;
  uint local_94;
  int local_90;
  int local_8c;
  int local_88;
  int local_84;
  uint local_80;
  u_long local_7c;
  u_long local_78;
  u_long local_74;
  u_long local_70;
  char local_69;
  u_long *local_68;
  uint local_64;
  int local_60;
  uint local_5c;
  LONG local_58;
  uint local_54;
  int local_50;
  uint local_4c;
  int local_48;
  u_long local_44;
  uint local_40;
  u_long local_3c;
  uint local_38;
  u_long local_34;
  uint local_30;
  int local_28;
  int local_24;
  uint local_20;
  uint local_1c;
  int local_18;
  undefined4 local_14;
  u_long *local_10;
  char *local_c;
  int local_8;
  
                    /* 0xcc920  11  InsertTerm */
  bVar12 = 0;
  puStack_1254 = &stack0xfffffffc;
  puStack_1258 = &LAB_400ceefa;
  puStack_125c = (undefined1 *)*in_FS_OFFSET;
  *in_FS_OFFSET = &puStack_125c;
  iStack_1004 = param_1;
  local_10 = param_3;
  local_c = param_2;
  local_8 = param_1;
  if ((int)*param_3 < 0) {
    puStack_1254 = &stack0xfffffffc;
    FUN_400039f0();
    return local_14;
  }
  puVar9 = param_3;
  puVar10 = local_1244;
  for (iVar8 = 8; iVar8 != 0; iVar8 = iVar8 + -1) {
    *puVar10 = *puVar9;
    puVar9 = puVar9 + 1;
    puVar10 = puVar10 + 1;
  }
  FUN_40024450(local_1244,9);
  local_14 = 0;
  local_b0 = FUN_4000a75c(0x2000);
  local_b4 = 0x100;
  FUN_400bfc0c(local_8,local_c);
  if ((*(int *)(local_8 + 0x5b1) < 1) || (10 < *(int *)(local_8 + 0x5b1))) {
    local_b8 = *(short **)(local_8 + 0x584);
  }
  else {
    local_b8 = *(short **)(local_8 + 0x584 + *(int *)(local_8 + 0x5b1) * 4);
  }
  local_d0 = local_b8;
  local_c8 = GetFileSize((HANDLE)(int)local_b8[2],&local_cc);
  iVar8 = FUN_40026c7c(local_cc,local_c8,extraout_ECX);
  if ((extraout_EDX == 0) && (iVar8 == 0)) {
    local_1224 = 0x14;
    local_1220 = 0;
    local_121c = 0;
    local_1218 = 0;
    local_1214 = -2;
    FUN_40024450(&local_1224,8);
    FUN_40026c48((HANDLE)(int)local_d0[2],&local_1224,0x14);
    FUN_40023da0(&local_1224,8);
  }
  else {
    FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_00,0,0);
    FUN_40026c20((HANDLE)(int)local_d0[2],&local_1224,0x14);
    FUN_40023da0(&local_1224,8);
  }
  FUN_4000b1a8(local_1d4,local_c);
  local_24 = FUN_400c94a0(local_8,local_1d4,0);
  if (local_24 != 0) {
    FUN_4000b1a8(local_1d4,local_c);
    local_74 = FUN_400cc8dc((HANDLE)(int)local_d0[2],&local_70,&local_1224);
    local_3c = FUN_40026c7c(local_70,local_74,extraout_ECX_37);
    local_1e0 = 1;
    local_1d8 = 1;
    local_1dc = 1;
    local_1e8 = 0xffffffff;
    local_1e4 = 0xffffffff;
    local_38 = extraout_EDX_16;
    FUN_40024450(&local_1e8,8);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,&local_1e8,0x14,local_3c,local_38);
    local_ac = local_3c + 0x14;
    local_a8 = local_38 + (0xffffffeb < local_3c);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_1244,0x20,local_ac,local_a8);
    local_28 = local_1218;
    if (local_1218 == 0) {
      FUN_400276f8((HANDLE)(int)local_d0[1],(int)&local_1224,1);
      FUN_400277ec((HANDLE)(int)*local_d0,(int)&local_1224,1);
      FUN_400cbe1c(local_b8,local_1d4,extraout_ECX_38,local_3c,local_38);
    }
    else {
      local_44 = local_3c;
      local_40 = local_38;
      local_69 = '\0';
      if (local_24 == -0xcb) {
        iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),
                             *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
        local_1c = iVar8 + 1;
      }
      else if (local_24 == -0xcc) {
        local_1c = 1;
      }
      else {
        local_1c = FUN_40028978(*(int *)(local_d0 + 0x824),
                                *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
      }
      iVar8 = FUN_400cc234((int)(local_d0 + 0x403),local_1d4);
      if (iVar8 == 0) {
        FUN_400276f8((HANDLE)(int)local_d0[1],(int)&local_1224,*(int *)(local_d0 + 0x403));
        pcVar13 = local_1d4;
        iVar2 = 1;
        uVar3 = local_1c;
        uVar6 = local_44;
        uVar4 = local_40;
        iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),
                             *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -2);
        cVar1 = FUN_400cc090((HANDLE)(int)local_d0[1],(u_long *)(local_d0 + 0x403),-iVar8,iVar2,
                             uVar3,uVar6,uVar4,pcVar13);
        if (cVar1 == '\0') {
          FUN_400039f0();
          return local_14;
        }
      }
      else {
        if (local_1214 == -2) {
          local_34 = local_1218 + 1;
          local_30 = (int)local_34 >> 0x1f;
          FUN_400276f8((HANDLE)(int)local_d0[1],(int)&local_1224,local_34);
        }
        else {
          local_74 = GetFileSize((HANDLE)(int)local_d0[1],&local_70);
          local_84 = FUN_40026c7c(local_70,local_74,extraout_ECX_39);
          local_80 = extraout_EDX_17;
          uVar3 = FUN_40006e0e(local_84,extraout_EDX_17,extraout_ECX_40,0x800,0);
          local_34 = uVar3 + 1;
          local_30 = extraout_EDX_18 + (uint)(0xfffffffe < uVar3);
        }
        iVar8 = FUN_400cc2c4((HANDLE)(int)local_d0[1],(u_long *)(local_d0 + 0x403),local_11e8,
                             local_1c,local_44,local_40,local_1d4,local_34,
                             *(int *)(local_d0 + 0x403));
        if (iVar8 == -1) {
          FUN_400039f0();
          return local_14;
        }
        local_69 = '\x01';
        local_44 = -local_34;
        local_40 = -(local_30 + (local_34 != 0));
      }
      if (local_69 != '\0') {
        local_18 = *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -4;
        do {
          local_84 = FUN_40028978(*(int *)(local_d0 + 0x824),local_18);
          local_84 = local_84 + -1;
          local_80 = local_84 >> 0x1f;
          local_8c = 0x800;
          local_88 = 0;
          local_c4 = FUN_40006dc8(local_84,local_80,extraout_ECX_41,0x800);
          local_c0 = extraout_EDX_19;
          FUN_40026be0((HANDLE)(int)*local_d0,0,extraout_ECX_42,local_c4,extraout_EDX_19);
          FUN_40026c20((HANDLE)(int)*local_d0,local_9e8,0x800);
          FUN_40023da0(local_9e8,0xb);
          iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),local_18 + 1);
          local_1c = iVar8 + 1;
          iVar8 = FUN_400cc234((int)local_9e8,local_1d4);
          if (iVar8 == 0) {
            pcVar13 = local_1d4;
            iVar2 = 1;
            uVar3 = local_1c;
            uVar6 = local_44;
            uVar4 = local_40;
            iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),local_18);
            cVar1 = FUN_400cc090((HANDLE)(int)*local_d0,local_9e8,iVar8,iVar2,uVar3,uVar6,uVar4,
                                 pcVar13);
            if (cVar1 == '\0') {
              FUN_400039f0();
              return local_14;
            }
            goto LAB_400cee57;
          }
          if (local_1214 == -2) {
            local_34 = local_121c + 1;
            local_30 = (int)local_34 >> 0x1f;
            FUN_400277ec((HANDLE)(int)*local_d0,(int)&local_1224,local_34);
          }
          else {
            local_74 = GetFileSize((HANDLE)(int)*local_d0,&local_70);
            local_84 = FUN_40026c7c(local_70,local_74,extraout_ECX_43);
            local_80 = extraout_EDX_20;
            uVar3 = FUN_40006e0e(local_84,extraout_EDX_20,extraout_ECX_44,0x800,0);
            local_34 = uVar3 + 1;
            local_30 = extraout_EDX_21 + (uint)(0xfffffffe < uVar3);
          }
          iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),local_18);
          iVar8 = FUN_400cc2c4((HANDLE)(int)*local_d0,local_9e8,local_11e8,local_1c,local_44,
                               local_40,local_1d4,local_34,iVar8);
          if (iVar8 == -1) goto LAB_400cee57;
          local_44 = local_34;
          local_40 = local_30;
          local_18 = local_18 + -2;
        } while (-1 < local_18);
        bVar11 = 0xfffffffe < local_34;
        local_34 = local_34 + 1;
        local_30 = local_30 + bVar11;
        FUN_400277ec((HANDLE)(int)*local_d0,(int)&local_1224,local_34);
        pcVar13 = local_1d4;
        uVar6 = FUN_40028978(*(int *)(local_d0 + 0x824),0);
        uVar7 = FUN_400cbc6c((HANDLE)(int)*local_d0,local_9e8,local_34,local_44,uVar6,pcVar13);
        if ((char)uVar7 == '\0') {
          FUN_400039f0();
          return local_14;
        }
        FUN_40026be0((HANDLE)(int)*local_d0,0,extraout_ECX_45,0,0);
        local_34 = htonl(local_34);
        local_30 = (int)local_34 >> 0x1f;
        FUN_40026c48((HANDLE)(int)*local_d0,&local_34,4);
        local_34 = ntohl(local_34);
        local_30 = (int)local_34 >> 0x1f;
      }
    }
    goto LAB_400cee57;
  }
  iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),*(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
  local_70 = *(u_long *)(local_d0 + (iVar8 + -1) * 6 + 0x40f);
  iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),*(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
  local_74 = *(u_long *)(local_d0 + (iVar8 + -1) * 6 + 0x40d);
  local_5c = FUN_40026c7c(local_70,local_74,extraout_ECX_01);
  local_58 = extraout_EDX_00;
  FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_02,local_5c,extraout_EDX_00);
  FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
  FUN_40023da0((u_long *)(local_d0 + 0x806),8);
  if (*(int *)(local_d0 + 0x808) == -0x3e9) {
    local_64 = local_5c;
    local_60 = local_58;
    FUN_40023da0(local_1244,9);
    local_20 = FUN_400caf48(local_8,&local_64,local_1244,&local_1c);
    FUN_40024450(local_1244,9);
    FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_20,local_64,local_60);
    FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    uVar7 = extraout_ECX_21;
    if (local_1c == 0) {
      local_84 = local_20 - 1;
      local_80 = local_84 >> 0x1f;
      local_8c = 0x28;
      local_88 = 0;
      uVar3 = FUN_40006dc8(local_84,local_80,extraout_ECX_21,0x28);
      local_ac = local_5c + uVar3 + 0x14;
      local_a8 = local_58 + extraout_EDX_08 + (uint)(0xffffffeb < uVar3) +
                 (uint)CARRY4(local_5c,uVar3 + 0x14);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_1244,0x20,local_ac,local_a8);
      uVar7 = extraout_ECX_22;
    }
    if (*(int *)(local_d0 + 0x80a) == 0) {
      local_d0[0x80a] = 1;
      local_d0[0x80b] = 0;
      local_d0[0x80c] = 1;
      local_d0[0x80d] = 0;
      FUN_40024450((u_long *)(local_d0 + 0x806),8);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_64,
                   local_60);
      local_ac = local_64 + 0x14;
      local_a8 = local_60 + (uint)(0xffffffeb < local_64);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_1244,0x20,local_ac,local_a8);
      FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_23,local_5c,local_58);
      FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
      *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
      FUN_40024450((u_long *)(local_d0 + 0x806),8);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_5c,
                   local_58);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    }
    else if (*(int *)(local_d0 + 0x80c) < *(int *)(local_d0 + 0x80e)) {
      *(int *)(local_d0 + 0x80c) = *(int *)(local_d0 + 0x80c) + 1;
      *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
      FUN_40024450((u_long *)(local_d0 + 0x806),8);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_64,
                   local_60);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
      if ((int)local_20 < 0) {
        local_ac = 0x14;
        local_a8 = 0;
        local_84 = *(int *)(local_d0 + 0x80c) + -1;
        local_80 = local_84 >> 0x1f;
        local_8c = 0x20;
        local_88 = 0;
        uVar3 = FUN_40006dc8(local_84,local_80,extraout_ECX_24,0x20);
        bVar11 = CARRY4(local_ac,local_64);
        uVar4 = local_ac + local_64;
        local_ac = uVar4 + uVar3;
        local_a8 = local_a8 + local_60 + (uint)bVar11 + extraout_EDX_09 + (uint)CARRY4(uVar4,uVar3);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_1244,0x20,local_ac,local_a8);
        uVar7 = extraout_ECX_25;
      }
      else {
        uVar7 = extraout_ECX_24;
        if (local_b4 < *(int *)(local_d0 + 0x80c)) {
          local_b4 = *(int *)(local_d0 + 0x80c);
          FUN_400029c8((int *)&local_b0,local_b4 * 0x20 + 1);
          uVar7 = extraout_ECX_26;
        }
        local_68 = local_b0;
        local_84 = local_1c - 1;
        local_80 = local_84 >> 0x1f;
        local_8c = 0x20;
        local_88 = 0;
        local_ac = 0x14;
        local_a8 = 0;
        uVar3 = FUN_40006dc8(local_84,local_80,uVar7,0x20);
        bVar11 = CARRY4(local_ac,local_64);
        uVar4 = local_ac + local_64;
        local_ac = uVar4 + uVar3;
        local_a8 = local_a8 + local_60 + (uint)bVar11 + extraout_EDX_10 + (uint)CARRY4(uVar4,uVar3);
        FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_27,local_ac,local_a8);
        FUN_40026c20((HANDLE)(int)local_d0[2],local_68 + 8,
                     (*(int *)(local_d0 + 0x80c) - local_1c) * 0x20);
        FUN_40002b84(local_1244,local_68,0x20);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,
                     ((*(int *)(local_d0 + 0x80c) - local_1c) + 1) * 0x20,local_ac,local_a8);
        uVar7 = extraout_ECX_28;
      }
      FUN_40026be0((HANDLE)(int)local_d0[2],0,uVar7,local_5c,local_58);
      FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
      *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
      FUN_40024450((u_long *)(local_d0 + 0x806),8);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_5c,
                   local_58);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    }
    else {
      if (local_b4 < *(int *)(local_d0 + 0x80c) + 1) {
        local_b4 = *(int *)(local_d0 + 0x80c) + 1;
        FUN_400029c8((int *)&local_b0,local_b4 * 0x20 + 1);
        uVar7 = extraout_ECX_29;
      }
      local_68 = local_b0;
      local_ac = local_64 + 0x14;
      local_a8 = local_60 + (uint)(0xffffffeb < local_64);
      FUN_40026be0((HANDLE)(int)local_d0[2],0,uVar7,local_ac,local_a8);
      FUN_40026c20((HANDLE)(int)local_d0[2],local_68,*(int *)(local_d0 + 0x80c) << 5);
      if ((int)local_20 < 0) {
        FUN_40002b84(local_1244,local_68 + *(int *)(local_d0 + 0x80c) * 8,0x20);
      }
      else {
        FUN_40002b84(local_68 + (local_1c - 1) * 8,local_68 + local_1c * 8,
                     ((*(int *)(local_d0 + 0x80c) + 1) - local_1c) * 0x20);
        FUN_40002b84(local_1244,local_68 + (local_1c - 1) * 8,0x20);
      }
      local_1e8 = *(u_long *)(local_d0 + 0x806);
      local_1e4 = *(undefined4 *)(local_d0 + 0x808);
      local_1d8 = *(int *)(local_d0 + 0x80e);
      local_1e0 = (int)(*(int *)(local_d0 + 0x80c) + 1U) >> 1;
      if (local_1e0 < 0) {
        local_1e0 = local_1e0 + (uint)((*(int *)(local_d0 + 0x80c) + 1U & 1) != 0);
      }
      local_1dc = local_1e0;
      DVar5 = FUN_400cc8dc((HANDLE)(int)local_d0[2],(LPDWORD)(local_d0 + 0x808),&local_1224);
      *(DWORD *)(local_d0 + 0x806) = DVar5;
      *(int *)(local_d0 + 0x80c) = (*(int *)(local_d0 + 0x80c) + 1) - local_1dc;
      *(undefined4 *)(local_d0 + 0x80a) = *(undefined4 *)(local_d0 + 0x80c);
      FUN_40024450((u_long *)(local_d0 + 0x806),8);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_64,
                   local_60);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
      uVar7 = extraout_ECX_30;
      if ((int)local_1c <= *(int *)(local_d0 + 0x80c)) {
        local_84 = local_1c - 1;
        local_80 = local_84 >> 0x1f;
        local_8c = 0x20;
        local_88 = 0;
        local_ac = 0x14;
        local_a8 = 0;
        uVar3 = FUN_40006dc8(local_84,local_80,extraout_ECX_30,0x20);
        bVar11 = CARRY4(local_ac,local_64);
        uVar4 = local_ac + local_64;
        local_ac = uVar4 + uVar3;
        local_a8 = local_a8 + local_60 + (uint)bVar11 + extraout_EDX_11 + (uint)CARRY4(uVar4,uVar3);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_b0 + local_1c * 8 + -8,
                     ((*(int *)(local_d0 + 0x80c) - local_1c) + 1) * 0x20,local_ac,local_a8);
        uVar7 = extraout_ECX_31;
      }
      local_c4 = FUN_40026c7c(*(int *)(local_d0 + 0x808),*(int *)(local_d0 + 0x806),uVar7);
      local_c0 = extraout_EDX_12;
      FUN_40024450(&local_1e8,8);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,&local_1e8,0x14,local_c4,local_c0);
      FUN_40023da0(&local_1e8,8);
      local_68 = local_b0;
      FUN_40002b84(local_b0 + *(int *)(local_d0 + 0x80c) * 8,local_b0,local_1dc << 5);
      FUN_40002e98(local_68 + (local_1dc + 1) * 8,(local_1d8 - local_1dc) * 0x20,0);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,local_1d8 << 5,
                   local_c4 + 0x14,local_c0 + (uint)(0xffffffeb < local_c4));
      puVar9 = local_b0;
      puVar10 = local_1210;
      for (iVar8 = 8; iVar8 != 0; iVar8 = iVar8 + -1) {
        *puVar10 = *puVar9;
        puVar9 = puVar9 + (uint)bVar12 * -2 + 1;
        puVar10 = puVar10 + (uint)bVar12 * -2 + 1;
      }
      FUN_40023da0(local_1210,9);
      local_11f0 = *(undefined4 *)(local_d0 + 0x806);
      local_11ec = *(undefined4 *)(local_d0 + 0x808);
      FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_32,local_5c,local_58);
      FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
      FUN_40023da0((u_long *)(local_d0 + 0x806),8);
      *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
      *(int *)(local_d0 + 0x80c) = *(int *)(local_d0 + 0x80c) + 1;
      local_68 = FUN_4000a75c(*(int *)(local_d0 + 0x80c) * 0x28);
      FUN_40026c20((HANDLE)(int)local_d0[2],local_68,(*(int *)(local_d0 + 0x80c) + -1) * 0x28);
      if (0 < *(int *)(local_d0 + 0x80c) + -1) {
        local_18 = 1;
        local_d4 = *(int *)(local_d0 + 0x80c) + -1;
        do {
          FUN_40023da0(local_68 + (local_18 + -1) * 10,10);
          local_18 = local_18 + 1;
          local_d4 = local_d4 + -1;
        } while (local_d4 != 0);
      }
      FUN_400cc7a0((int)local_68,*(int *)(local_d0 + 0x80c),local_1210);
      if (*(int *)(local_d0 + 0x80e) < *(int *)(local_d0 + 0x80c)) {
        local_74 = FUN_400cc8dc((HANDLE)(int)local_d0[2],&local_70,&local_1224);
        local_5c = FUN_40026c7c(local_70,local_74,extraout_ECX_33);
        iVar8 = *(int *)(local_d0 + 0x80c);
        if (iVar8 < 0) {
          iVar8 = iVar8 + 3;
        }
        *(int *)(local_d0 + 0x80e) = ((iVar8 >> 2) + 1) * 4;
        local_58 = extraout_EDX_13;
        FUN_40024450((u_long *)(local_d0 + 0x806),8);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_5c,
                     local_58);
        FUN_40023da0((u_long *)(local_d0 + 0x806),8);
        if (0 < *(int *)(local_d0 + 0x80c)) {
          local_18 = 1;
          local_d4 = *(int *)(local_d0 + 0x80c);
          do {
            FUN_40024450(local_68 + (local_18 + -1) * 10,10);
            local_18 = local_18 + 1;
            local_d4 = local_d4 + -1;
          } while (local_d4 != 0);
        }
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,
                     *(int *)(local_d0 + 0x80c) * 0x28,local_5c + 0x14,
                     local_58 + (uint)(0xffffffeb < local_5c));
        if (*(int *)(local_d0 + 0x80c) < *(int *)(local_d0 + 0x80e)) {
          FUN_40002e98(local_68,*(int *)(local_d0 + 0x80c) * 0x28,0);
          if (0 < *(int *)(local_d0 + 0x80e) - *(int *)(local_d0 + 0x80c)) {
            local_18 = 1;
            local_d4 = *(int *)(local_d0 + 0x80e) - *(int *)(local_d0 + 0x80c);
            do {
              FUN_40024450(local_68 + (local_18 + -1) * 10,10);
              local_18 = local_18 + 1;
              local_d4 = local_d4 + -1;
            } while (local_d4 != 0);
          }
          uVar3 = *(int *)(local_d0 + 0x80c) * 0x28;
          FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,
                       (*(int *)(local_d0 + 0x80e) - *(int *)(local_d0 + 0x80c)) * 0x28,
                       local_5c + 0x14 + uVar3,
                       local_58 + (uint)(0xffffffeb < local_5c) + ((int)uVar3 >> 0x1f) +
                       (uint)CARRY4(local_5c + 0x14,uVar3));
        }
        local_84 = *(int *)(local_d0 + 0x403) + -1;
        local_80 = local_84 >> 0x1f;
        local_8c = 0x800;
        local_88 = 0;
        local_94 = 0x14;
        local_90 = 0;
        local_9c = FUN_40028978(*(int *)(local_d0 + 0x824),
                                *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
        local_9c = local_9c + -1;
        local_98 = local_9c >> 0x1f;
        local_a4 = 0xc;
        local_a0 = 0;
        uVar3 = FUN_40006dc8(local_84,local_80,extraout_ECX_34,local_8c);
        uVar4 = uVar3 + local_94;
        iVar8 = extraout_EDX_14 + local_90 + (uint)CARRY4(uVar3,local_94);
        uVar3 = FUN_40006dc8(local_9c,local_98,extraout_ECX_35,local_a4);
        local_c4 = uVar3 + uVar4;
        local_c0 = extraout_EDX_15 + iVar8 + (uint)CARRY4(uVar3,uVar4);
        FUN_40026be0((HANDLE)(int)local_d0[1],0,extraout_ECX_36,local_c4,local_c0);
        iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),
                             *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
        *(u_long *)(local_d0 + (iVar8 + -1) * 6 + 0x40d) = local_74;
        iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),
                             *(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1);
        *(u_long *)(local_d0 + (iVar8 + -1) * 6 + 0x40f) = local_70;
        local_70 = htonl(local_70);
        local_7c = htonl(local_74);
        local_78 = local_70;
        local_74 = local_7c;
        FUN_40026c48((HANDLE)(int)local_d0[1],&local_7c,8);
      }
      else {
        FUN_40024450((u_long *)(local_d0 + 0x806),8);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_5c,
                     local_58);
        FUN_40023da0((u_long *)(local_d0 + 0x806),8);
        if (0 < *(int *)(local_d0 + 0x80c)) {
          local_18 = 1;
          local_d4 = *(int *)(local_d0 + 0x80c);
          do {
            FUN_40024450(local_68 + (local_18 + -1) * 10,10);
            local_18 = local_18 + 1;
            local_d4 = local_d4 + -1;
          } while (local_d4 != 0);
        }
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,
                     *(int *)(local_d0 + 0x80c) * 0x28,local_5c + 0x14,
                     local_58 + (uint)(0xffffffeb < local_5c));
      }
      uVar7 = *in_FS_OFFSET;
      *in_FS_OFFSET = &stack0xffffed98;
      FUN_400029b0((int)local_68);
      *in_FS_OFFSET = uVar7;
    }
    goto LAB_400cee57;
  }
  if (*(int *)(local_d0 + 0x80a) < 1) {
    local_d0[0x80a] = 1;
    local_d0[0x80b] = 0;
    local_d0[0x80c] = 1;
    local_d0[0x80d] = 0;
    iVar8 = FUN_40028978(*(int *)(local_d0 + 0x824),*(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1)
    ;
    iVar8 = *(int *)(local_d0 + (iVar8 + -1) * 6 + 0x40d);
    iVar2 = FUN_40028978(*(int *)(local_d0 + 0x824),*(int *)(*(int *)(local_d0 + 0x824) + 0xc) + -1)
    ;
    local_c4 = FUN_40026c7c(*(int *)(local_d0 + (iVar2 + -1) * 6 + 0x40f),iVar8,extraout_ECX_04);
    local_c0 = extraout_EDX_01;
    FUN_40024450((u_long *)(local_d0 + 0x806),8);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_c4,local_c0
                );
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    local_ac = local_c4 + 0x14;
    local_a8 = local_c0 + (uint)(0xffffffeb < local_c4);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_1244,0x20,local_ac,local_a8);
    goto LAB_400cee57;
  }
  local_20 = 0xffffffff;
  local_4c = 0xffffffff;
  local_48 = -1;
  local_54 = 0xffffffff;
  local_50 = -1;
  uVar7 = extraout_ECX_03;
  local_64 = local_5c;
  local_60 = local_58;
  while (local_70 != 0xffffffff) {
    FUN_40023da0(local_1244,9);
    local_20 = FUN_400cac04(local_8,local_1244,&local_1c,local_64,local_60);
    FUN_40024450(local_1244,9);
    uVar7 = extraout_ECX_05;
    if ((-1 < (int)local_20) || (*(int *)(local_d0 + 0x808) == -1)) break;
    if (*(int *)(local_d0 + 0x80c) < *(int *)(local_d0 + 0x80e)) {
      local_ac = 0x14;
      local_a8 = 0;
      local_84 = *(int *)(local_d0 + 0x80c);
      local_80 = local_84 >> 0x1f;
      local_8c = 0x20;
      local_88 = 0;
      uVar3 = FUN_40006dc8(local_84,local_80,extraout_ECX_05,0x20);
      local_4c = local_64 + local_ac + uVar3;
      local_48 = local_60 + local_a8 + (uint)CARRY4(local_64,local_ac) + extraout_EDX_02 +
                 (uint)CARRY4(local_64 + local_ac,uVar3);
      local_54 = local_64;
      local_50 = local_60;
      uVar7 = extraout_ECX_06;
    }
    else {
      local_4c = 0xffffffff;
      local_48 = -1;
    }
    local_64 = FUN_40026c7c(*(int *)(local_d0 + 0x808),*(int *)(local_d0 + 0x806),uVar7);
    local_70 = *(u_long *)(local_d0 + 0x808);
    local_60 = extraout_EDX_03;
    FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_07,local_64,extraout_EDX_03);
    FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    uVar7 = extraout_ECX_08;
  }
  if (local_1c == 0) goto LAB_400cee57;
  if (*(int *)(local_d0 + 0x80c) < *(int *)(local_d0 + 0x80e)) {
    *(int *)(local_d0 + 0x80c) = *(int *)(local_d0 + 0x80c) + 1;
    *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
    FUN_40024450((u_long *)(local_d0 + 0x806),8);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_64,local_60
                );
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    if ((int)local_20 < 0) {
      local_ac = 0x14;
      local_a8 = 0;
      local_84 = 0x20;
      local_80 = 0;
      local_8c = *(int *)(local_d0 + 0x80c) + -1;
      local_88 = local_8c >> 0x1f;
      uVar3 = FUN_40006dc8(0x20,0,extraout_ECX_09,local_8c);
      bVar11 = CARRY4(uVar3,local_ac);
      uVar3 = uVar3 + local_ac;
      local_ac = local_64 + uVar3;
      local_a8 = local_60 + extraout_EDX_04 + local_a8 + (uint)bVar11 + (uint)CARRY4(local_64,uVar3)
      ;
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_1244,0x20,local_ac,local_a8);
      uVar7 = extraout_ECX_10;
    }
    else {
      uVar7 = extraout_ECX_09;
      if (local_b4 < *(int *)(local_d0 + 0x80c)) {
        local_b4 = *(int *)(local_d0 + 0x80c);
        FUN_400029c8((int *)&local_b0,local_b4 << 5);
        uVar7 = extraout_ECX_11;
      }
      local_68 = local_b0;
      local_ac = 0x14;
      local_a8 = 0;
      local_84 = local_1c - 1;
      local_80 = local_84 >> 0x1f;
      local_8c = 0x20;
      local_88 = 0;
      uVar3 = FUN_40006dc8(local_84,local_80,uVar7,0x20);
      bVar11 = CARRY4(local_64,local_ac);
      uVar4 = local_64 + local_ac;
      local_ac = uVar4 + uVar3;
      local_a8 = local_60 + local_a8 + (uint)bVar11 + extraout_EDX_05 + (uint)CARRY4(uVar4,uVar3);
      FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_12,local_ac,local_a8);
      FUN_40026c20((HANDLE)(int)local_d0[2],local_68 + 8,
                   (*(int *)(local_d0 + 0x80c) - local_1c) * 0x20);
      FUN_40002b84(local_1244,local_68,0x20);
      FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,
                   ((*(int *)(local_d0 + 0x80c) - local_1c) + 1) * 0x20,local_ac,local_a8);
      uVar7 = extraout_ECX_13;
    }
  }
  else {
    if (local_b4 < (*(int *)(local_d0 + 0x80c) + 1) * 2 + 1) {
      local_b4 = (*(int *)(local_d0 + 0x80c) + 1) * 2 + 1;
      FUN_400029c8((int *)&local_b0,local_b4 * 0x20 + 1);
      uVar7 = extraout_ECX_14;
    }
    local_68 = local_b0;
    local_ac = local_64 + 0x14;
    local_a8 = local_60 + (uint)(0xffffffeb < local_64);
    FUN_40026be0((HANDLE)(int)local_d0[2],0,uVar7,local_ac,local_a8);
    FUN_40026c20((HANDLE)(int)local_d0[2],local_68,*(int *)(local_d0 + 0x80c) << 5);
    if ((int)local_20 < 0) {
      FUN_40002b84(local_1244,local_68 + *(int *)(local_d0 + 0x80c) * 8,0x20);
    }
    else {
      FUN_40002b84(local_68 + (local_1c - 1) * 8,local_68 + local_1c * 8,
                   ((*(int *)(local_d0 + 0x80c) + 1) - local_1c) * 0x20);
      FUN_40002b84(local_1244,local_68 + (local_1c - 1) * 8,0x20);
    }
    if (local_48 == 0) {
      if (local_4c == 0) {
LAB_400cd478:
        *(int *)(local_d0 + 0x80c) = *(int *)(local_d0 + 0x80c) + 1;
        local_1e8 = *(u_long *)(local_d0 + 0x806);
        local_1e4 = *(undefined4 *)(local_d0 + 0x808);
        local_1d8 = *(int *)(local_d0 + 0x80c);
        local_1e0 = (int)*(uint *)(local_d0 + 0x80c) >> 1;
        if (local_1e0 < 0) {
          local_1e0 = local_1e0 + (uint)((*(uint *)(local_d0 + 0x80c) & 1) != 0);
        }
        *(int *)(local_d0 + 0x80c) = *(int *)(local_d0 + 0x80c) - local_1e0;
        if (local_60 == local_58 && local_64 == local_5c) {
          *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
        }
        else {
          *(undefined4 *)(local_d0 + 0x80a) = *(undefined4 *)(local_d0 + 0x80c);
        }
        local_1dc = local_1e0;
        DVar5 = FUN_400cc8dc((HANDLE)(int)local_d0[2],(LPDWORD)(local_d0 + 0x808),&local_1224);
        *(DWORD *)(local_d0 + 0x806) = DVar5;
        FUN_40024450((u_long *)(local_d0 + 0x806),8);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_64,
                     local_60);
        FUN_40023da0((u_long *)(local_d0 + 0x806),8);
        uVar7 = extraout_ECX_17;
        if ((int)local_1c <= *(int *)(local_d0 + 0x80c)) {
          local_84 = local_1c - 1;
          local_80 = local_84 >> 0x1f;
          local_8c = 0x20;
          local_88 = 0;
          local_ac = 0x14;
          local_a8 = 0;
          uVar3 = FUN_40006dc8(local_84,local_80,extraout_ECX_17,0x20);
          bVar11 = CARRY4(uVar3,local_ac);
          uVar3 = uVar3 + local_ac;
          local_ac = uVar3 + local_64;
          local_a8 = extraout_EDX_06 + local_a8 + (uint)bVar11 + local_60 +
                     (uint)CARRY4(uVar3,local_64);
          FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68 + (local_1c - 1) * 8,
                       ((*(int *)(local_d0 + 0x80c) + 1) - local_1c) * 0x20,local_ac,local_a8);
          uVar7 = extraout_ECX_18;
        }
        local_c4 = FUN_40026c7c(*(int *)(local_d0 + 0x808),*(int *)(local_d0 + 0x806),uVar7);
        local_c0 = extraout_EDX_07;
        FUN_40024450(&local_1e8,8);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,&local_1e8,0x14,local_c4,local_c0);
        FUN_40023da0(&local_1e8,8);
        local_ac = local_c4 + 0x14;
        local_a8 = local_c0 + (uint)(0xffffffeb < local_c4);
        FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,
                     local_68 + *(int *)(local_d0 + 0x80c) * 8,local_1d8 << 5,local_ac,local_a8);
        uVar7 = extraout_ECX_19;
        goto LAB_400cd768;
      }
    }
    else if (local_48 < 1) goto LAB_400cd478;
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68,0x20,local_4c,local_48);
    local_ac = local_64 + 0x14;
    local_a8 = local_60 + (uint)(0xffffffeb < local_64);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_68 + 8,
                 *(int *)(local_d0 + 0x80c) << 5,local_ac,local_a8);
    FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_15,local_54,local_50);
    FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    *(int *)(local_d0 + 0x80c) = *(int *)(local_d0 + 0x80c) + 1;
    if (local_50 != local_58 || local_54 != local_5c) {
      *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
    }
    FUN_40024450((u_long *)(local_d0 + 0x806),8);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_54,local_50
                );
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    uVar7 = extraout_ECX_16;
  }
LAB_400cd768:
  if (local_60 != local_58 || local_64 != local_5c) {
    FUN_40026be0((HANDLE)(int)local_d0[2],0,uVar7,local_5c,local_58);
    FUN_40026c20((HANDLE)(int)local_d0[2],local_d0 + 0x806,0x14);
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
    *(int *)(local_d0 + 0x80a) = *(int *)(local_d0 + 0x80a) + 1;
    FUN_40024450((u_long *)(local_d0 + 0x806),8);
    FUN_400274c4((HANDLE)(int)local_d0[2],(int *)&local_1224,local_d0 + 0x806,0x14,local_5c,local_58
                );
    FUN_40023da0((u_long *)(local_d0 + 0x806),8);
  }
LAB_400cee57:
  if (local_1214 == -2) {
    FUN_40024450(&local_1224,8);
    FUN_40026be0((HANDLE)(int)local_d0[2],0,extraout_ECX_46,0,0);
    FUN_40026c48((HANDLE)(int)local_d0[2],&local_1224,0x14);
    FUN_40023da0(&local_1224,8);
  }
  *in_FS_OFFSET = puStack_125c;
  puStack_1254 = (undefined1 *)0x400cef01;
  puStack_1258 = (undefined1 *)0x400ceecc;
  FUN_40023da0(local_1244,9);
  puStack_125c = &LAB_400ceeef;
  uVar7 = *in_FS_OFFSET;
  *in_FS_OFFSET = &stack0xffffeda0;
  puStack_1258 = &stack0xfffffffc;
  FUN_400029b0((int)local_b0);
  *in_FS_OFFSET = uVar7;
  return 0;
}



/* ===== UMARCI @ 400aef88 ===== */

void UMARCI(undefined4 param_1,undefined4 param_2,undefined4 param_3,int *param_4,byte *param_5)

{
  uint uVar1;
  char *pcVar2;
  undefined4 extraout_ECX;
  undefined4 extraout_EDX;
  undefined4 *in_FS_OFFSET;
  int *piVar3;
  undefined4 uStack_30;
  undefined1 *puStack_2c;
  undefined1 *puStack_28;
  undefined *local_18 [2];
  undefined4 local_10;
  undefined4 local_c;
  int local_8;
  
                    /* 0xaef88  6  UMARCI */
  puStack_28 = &stack0xfffffffc;
  local_8 = 0;
  local_18[0] = (undefined *)0x0;
  puStack_2c = &LAB_400af082;
  uStack_30 = *in_FS_OFFSET;
  *in_FS_OFFSET = &uStack_30;
  local_10 = param_2;
  local_c = param_1;
  FUN_40003f78((int *)local_18);
  FUN_40004140(&local_8,(char *)param_5);
  piVar3 = &local_8;
  uVar1 = FUN_40004208(local_8);
  FUN_40004410(local_8,2,uVar1,piVar3);
  CharUpperBuffA((LPSTR)param_5,1);
  switch(*param_5 - 0x30) {
  case 0:
    FUN_400ae284(*param_5 - 0x30,extraout_EDX,extraout_ECX,(int)&stack0xfffffffc);
    break;
  case 1:
    FUN_400ae45c();
    break;
  case 2:
    FUN_400ae6d0();
    break;
  case 3:
    FUN_400ae87c();
    break;
  case 4:
    FUN_400adf34();
    break;
  case 5:
    FUN_400aeb4c();
  }
  pcVar2 = FUN_400043cc(local_18[0]);
  FUN_40087f50(param_4,pcVar2,(uint *)&DAT_400e7210);
  *in_FS_OFFSET = uStack_30;
  puStack_28 = &LAB_400af089;
  puStack_2c = (undefined1 *)0x400af079;
  FUN_40003f78((int *)local_18);
  puStack_2c = (undefined1 *)0x400af081;
  FUN_40003f78(&local_8);
  return;
}


