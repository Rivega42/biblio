/* Ghidra pseudo-C of UNIFOR @ IRBIS64.dll (600s timeout) */

/* ===== UNIFOR @ 4009fbf0 ===== */

/* WARNING: Heritage AFTER dead removal. Example location: EAX : 0x400a8923 */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */
/* WARNING: Restarted to delay deadcode elimination for space: register */
/* WARNING: Exceeded maximum restarts with more pending */

void UNIFOR(int *param_1,undefined *param_2,undefined4 param_3,uint *param_4,byte *param_5,
           undefined1 *param_6,undefined *param_7,uint *param_8,undefined *param_9,char *param_10,
           int param_11)

{
  byte bVar1;
  char cVar2;
  int iVar3;
  undefined *puVar4;
  uint *puVar5;
  undefined1 *puVar6;
  uint uVar7;
  undefined4 *puVar8;
  undefined4 *puVar9;
  undefined4 uVar10;
  uint uVar11;
  char *pcVar12;
  LPCSTR pCVar13;
  FARPROC pFVar14;
  LPSTR pCVar15;
  LPCCH lpBuffer;
  int iVar16;
  undefined4 extraout_ECX;
  int extraout_ECX_00;
  int extraout_ECX_01;
  int extraout_ECX_02;
  int extraout_ECX_03;
  int extraout_ECX_04;
  int extraout_ECX_05;
  undefined1 *extraout_ECX_06;
  undefined1 *extraout_ECX_07;
  undefined1 *extraout_ECX_08;
  undefined1 *extraout_ECX_09;
  undefined1 *extraout_ECX_10;
  undefined1 *extraout_ECX_11;
  undefined1 *extraout_ECX_12;
  int extraout_ECX_13;
  int extraout_ECX_14;
  int extraout_ECX_15;
  undefined1 *extraout_ECX_16;
  int extraout_ECX_17;
  int extraout_ECX_18;
  int extraout_ECX_19;
  int extraout_ECX_20;
  undefined1 *extraout_ECX_21;
  int extraout_ECX_22;
  int extraout_ECX_23;
  int extraout_ECX_24;
  int extraout_ECX_25;
  int extraout_ECX_26;
  int extraout_ECX_27;
  undefined1 *extraout_ECX_28;
  int extraout_ECX_29;
  int extraout_ECX_30;
  int extraout_ECX_31;
  int extraout_ECX_32;
  undefined4 extraout_ECX_33;
  undefined4 extraout_ECX_34;
  int extraout_ECX_35;
  int extraout_ECX_36;
  int extraout_ECX_37;
  int extraout_ECX_38;
  undefined4 extraout_ECX_39;
  int extraout_ECX_40;
  undefined4 extraout_ECX_41;
  undefined4 extraout_ECX_42;
  undefined4 extraout_ECX_43;
  undefined4 extraout_ECX_44;
  undefined4 extraout_ECX_45;
  int extraout_ECX_46;
  int extraout_ECX_47;
  int extraout_ECX_48;
  int extraout_ECX_49;
  int extraout_ECX_50;
  int extraout_ECX_51;
  int extraout_ECX_52;
  int extraout_ECX_53;
  int extraout_ECX_54;
  int extraout_ECX_55;
  int extraout_ECX_56;
  int extraout_ECX_57;
  int extraout_ECX_58;
  int extraout_ECX_59;
  int extraout_ECX_60;
  int extraout_ECX_61;
  int extraout_ECX_62;
  int extraout_ECX_63;
  int extraout_ECX_64;
  int extraout_ECX_65;
  int extraout_ECX_66;
  int extraout_ECX_67;
  int extraout_ECX_68;
  int extraout_ECX_69;
  int extraout_ECX_70;
  int extraout_ECX_71;
  undefined4 extraout_ECX_72;
  int extraout_ECX_73;
  int extraout_ECX_74;
  int extraout_ECX_75;
  int extraout_ECX_76;
  int extraout_ECX_77;
  int extraout_ECX_78;
  int extraout_ECX_79;
  undefined4 extraout_ECX_80;
  undefined4 extraout_ECX_81;
  undefined4 extraout_ECX_82;
  undefined4 extraout_ECX_83;
  undefined4 extraout_ECX_84;
  int extraout_ECX_85;
  int extraout_ECX_86;
  int extraout_ECX_87;
  int extraout_ECX_88;
  int extraout_ECX_89;
  int extraout_ECX_90;
  int extraout_ECX_91;
  undefined4 extraout_ECX_92;
  undefined4 extraout_EDX;
  undefined3 uVar17;
  undefined4 extraout_EDX_00;
  undefined4 extraout_EDX_01;
  undefined4 extraout_EDX_02;
  int extraout_EDX_03;
  undefined4 extraout_EDX_04;
  int extraout_EDX_05;
  int *in_FS_OFFSET;
  undefined1 uVar18;
  undefined1 uVar19;
  bool bVar20;
  float10 in_ST0;
  float10 in_ST1;
  int local_be4;
  int iStack_be0;
  char *pcStack_bdc;
  int *local_bd8;
  undefined *local_bd4;
  uint *puStack_bd0;
  undefined *puStack_bcc;
  uint *puStack_bc8;
  undefined *puStack_bc4;
  undefined *puStack_bc0;
  uint *puStack_bbc;
  int iStack_bb8;
  int iStack_bb4;
  int iStack_bb0;
  undefined4 *puStack_bac;
  undefined *puStack_ba8;
  byte *pbStack_ba4;
  byte *pbStack_ba0;
  int iStack_b9c;
  int iStack_b98;
  int *local_b94;
  int local_b90;
  LPCWSTR local_b8c;
  undefined4 *local_b88;
  int iStack_b84;
  int iStack_b80;
  int iStack_b7c;
  uint *puStack_b78;
  uint *puStack_b74;
  char *pcStack_b70;
  char *pcStack_b6c;
  int iStack_b68;
  int iStack_b64;
  int iStack_b60;
  char *pcStack_b5c;
  undefined *puStack_b58;
  int iStack_b54;
  undefined *puStack_b50;
  undefined *puStack_b4c;
  undefined *puStack_b48;
  int iStack_b44;
  byte *pbStack_b40;
  byte *pbStack_b3c;
  uint *puStack_b38;
  undefined *puStack_b34;
  char *pcStack_b30;
  undefined4 uStack_b2c;
  int iStack_b28;
  undefined *puStack_b24;
  int iStack_b20;
  byte *pbStack_b1c;
  byte *pbStack_b18;
  uint *puStack_b14;
  undefined *puStack_b10;
  undefined *puStack_b0c;
  uint *puStack_b08;
  int iStack_b04;
  int iStack_b00;
  int iStack_afc;
  undefined4 *puStack_af8;
  undefined4 *puStack_af4;
  undefined *puStack_af0;
  undefined *puStack_aec;
  undefined *puStack_ae8;
  undefined *puStack_ae4;
  int iStack_ae0;
  undefined4 *puStack_adc;
  int iStack_ad8;
  int iStack_ad4;
  BSTR local_ad0;
  BSTR pOStack_acc;
  undefined *local_ac8;
  int iStack_ac4;
  undefined *puStack_ac0;
  char *pcStack_abc;
  char *pcStack_ab8;
  int iStack_ab4;
  int iStack_ab0;
  int iStack_aac;
  uint *puStack_aa8;
  int iStack_aa4;
  char *pcStack_aa0;
  int iStack_a9c;
  undefined4 *puStack_a98;
  undefined4 *puStack_a94;
  int iStack_a90;
  undefined *puStack_a8c;
  uint *puStack_a88;
  int iStack_a84;
  int iStack_a80;
  int iStack_a7c;
  byte *pbStack_a78;
  uint *puStack_a74;
  int iStack_a70;
  int iStack_a6c;
  undefined *puStack_a68;
  undefined *puStack_a64;
  undefined *puStack_a60;
  undefined *puStack_a5c;
  int local_a58;
  int iStack_a54;
  int local_a50;
  undefined4 *local_a4c;
  int iStack_a48;
  int iStack_a44;
  uint *puStack_a40;
  undefined *puStack_a3c;
  int iStack_a38;
  undefined4 *puStack_a34;
  undefined4 *puStack_a30;
  undefined4 *puStack_a2c;
  undefined4 *puStack_a28;
  undefined4 *puStack_a24;
  undefined4 *puStack_a20;
  undefined4 *puStack_a1c;
  undefined4 *puStack_a18;
  int iStack_a14;
  undefined *puStack_a10;
  byte *pbStack_a0c;
  int *local_a08;
  int local_a04;
  undefined4 *puStack_a00;
  undefined4 *puStack_9fc;
  undefined4 *puStack_9f8;
  undefined4 *puStack_9f4;
  undefined4 *puStack_9f0;
  undefined4 *puStack_9ec;
  int iStack_9e8;
  byte *pbStack_9e4;
  byte *pbStack_9e0;
  undefined *puStack_9dc;
  byte *pbStack_9d8;
  LPCWSTR local_9d4;
  int local_9d0;
  undefined *puStack_9cc;
  int iStack_9c8;
  LPCSTR pCStack_9c4;
  undefined *local_9c0;
  uint *local_9bc;
  uint *puStack_9b8;
  uint *puStack_9b4;
  undefined4 *puStack_9b0;
  undefined4 *puStack_9ac;
  undefined4 *puStack_9a8;
  undefined4 *puStack_9a4;
  undefined4 *puStack_9a0;
  undefined4 *puStack_99c;
  undefined *puStack_998;
  byte *pbStack_994;
  undefined *puStack_990;
  undefined *puStack_98c;
  uint *puStack_988;
  undefined4 *puStack_984;
  undefined4 *puStack_980;
  undefined4 *puStack_97c;
  undefined4 *puStack_978;
  undefined4 *puStack_974;
  undefined *puStack_970;
  byte *pbStack_96c;
  char *pcStack_968;
  undefined4 *puStack_964;
  undefined4 *puStack_960;
  int iStack_95c;
  int iStack_958;
  undefined *puStack_954;
  int iStack_950;
  int iStack_94c;
  undefined4 *puStack_948;
  int iStack_944;
  int iStack_940;
  byte *pbStack_93c;
  int iStack_938;
  int iStack_934;
  char *pcStack_930;
  int iStack_92c;
  byte *pbStack_928;
  uint *puStack_924;
  byte *pbStack_920;
  uint *puStack_91c;
  undefined *puStack_918;
  BSTR local_914;
  int local_910;
  int iStack_90c;
  int iStack_908;
  int iStack_904;
  undefined *puStack_900;
  int iStack_8fc;
  undefined *puStack_8f8;
  int iStack_8f4;
  undefined *puStack_8f0;
  undefined *puStack_8ec;
  int iStack_8e8;
  uint *puStack_8e4;
  byte *pbStack_8e0;
  undefined *puStack_8dc;
  uint *puStack_8d8;
  int iStack_8d4;
  undefined *puStack_8d0;
  uint *puStack_8cc;
  undefined *local_8c8;
  undefined4 *puStack_8c4;
  undefined4 *puStack_8c0;
  undefined *puStack_8bc;
  undefined *local_8b8;
  undefined *local_8b4;
  undefined4 *puStack_8b0;
  undefined4 *puStack_8ac;
  undefined *puStack_8a8;
  undefined *puStack_8a4;
  byte *pbStack_8a0;
  int iStack_89c;
  char *pcStack_898;
  uint *puStack_894;
  int iStack_890;
  char *pcStack_88c;
  int iStack_888;
  uint *puStack_884;
  uint *puStack_880;
  uint *puStack_87c;
  int iStack_878;
  int iStack_874;
  int iStack_870;
  byte *pbStack_86c;
  int iStack_868;
  undefined *puStack_864;
  undefined *puStack_860;
  int iStack_85c;
  undefined4 *puStack_858;
  undefined *puStack_854;
  undefined *puStack_850;
  undefined *puStack_84c;
  undefined *puStack_848;
  BSTR local_844;
  int local_840;
  undefined *puStack_83c;
  undefined *puStack_838;
  int iStack_834;
  undefined *puStack_830;
  int iStack_82c;
  undefined *puStack_828;
  int iStack_824;
  undefined *puStack_820;
  int iStack_81c;
  int iStack_818;
  undefined *puStack_814;
  int iStack_810;
  undefined *puStack_80c;
  uint *puStack_808;
  undefined *puStack_804;
  byte *pbStack_800;
  uint *puStack_7fc;
  uint *puStack_7f8;
  undefined *puStack_7f4;
  undefined *puStack_7f0;
  undefined *puStack_7ec;
  undefined *puStack_7e8;
  int iStack_7e4;
  undefined *puStack_7e0;
  int iStack_7dc;
  int iStack_7d8;
  byte *pbStack_7d4;
  undefined *puStack_7d0;
  int iStack_7cc;
  byte *pbStack_7c8;
  int iStack_7c4;
  int iStack_7c0;
  undefined4 uStack_7bc;
  undefined4 uStack_7b8;
  int iStack_7b4;
  byte *pbStack_7b0;
  byte *pbStack_7ac;
  undefined4 uStack_7a8;
  undefined4 uStack_7a4;
  int iStack_7a0;
  byte *pbStack_79c;
  byte *pbStack_798;
  undefined4 uStack_794;
  undefined4 uStack_790;
  int iStack_78c;
  byte *pbStack_788;
  byte *pbStack_784;
  undefined4 uStack_780;
  undefined4 uStack_77c;
  int iStack_778;
  byte *pbStack_774;
  byte *pbStack_770;
  uint *puStack_76c;
  byte *pbStack_768;
  undefined4 uStack_764;
  int iStack_760;
  byte *pbStack_75c;
  undefined *puStack_758;
  int iStack_754;
  undefined *puStack_750;
  int iStack_74c;
  int iStack_748;
  undefined4 uStack_744;
  int iStack_740;
  undefined4 uStack_73c;
  undefined *puStack_738;
  int local_734;
  undefined4 uStack_730;
  int iStack_72c;
  undefined4 uStack_728;
  undefined *puStack_724;
  int iStack_720;
  undefined4 uStack_71c;
  int iStack_718;
  undefined4 uStack_714;
  undefined *puStack_710;
  undefined1 auStack_70c [4];
  int iStack_708;
  undefined4 *puStack_704;
  int iStack_700;
  undefined4 uStack_6fc;
  int iStack_6f8;
  int iStack_6f4;
  undefined4 uStack_6f0;
  byte *pbStack_6ec;
  byte *pbStack_6e8;
  byte *pbStack_6e4;
  undefined4 *puStack_6e0;
  undefined4 *puStack_6dc;
  byte *pbStack_6d8;
  char *pcStack_6d4;
  int iStack_6d0;
  undefined *puStack_6cc;
  int iStack_6c8;
  undefined *puStack_6c4;
  int iStack_6c0;
  int iStack_6bc;
  undefined *puStack_6b8;
  int iStack_6b4;
  undefined *puStack_6b0;
  int iStack_6ac;
  int iStack_6a8;
  undefined *puStack_6a4;
  undefined4 *puStack_6a0;
  int iStack_69c;
  int iStack_698;
  int iStack_694;
  undefined1 auStack_690 [4];
  int iStack_68c;
  int iStack_688;
  int iStack_684;
  undefined *puStack_680;
  int iStack_67c;
  int iStack_678;
  undefined *puStack_674;
  undefined *puStack_670;
  int iStack_66c;
  undefined *puStack_668;
  int iStack_664;
  undefined *puStack_660;
  undefined *puStack_65c;
  int iStack_658;
  int iStack_654;
  int iStack_650;
  undefined *puStack_64c;
  int iStack_648;
  undefined *puStack_644;
  undefined *puStack_640;
  byte *pbStack_63c;
  int iStack_638;
  int iStack_634;
  undefined *puStack_630;
  undefined1 auStack_62c [16];
  int local_61c;
  LPCSTR pCStack_618;
  undefined4 local_614;
  LPCSTR local_610;
  undefined4 local_60c;
  BSTR pOStack_608;
  BSTR pOStack_604;
  OLECHAR *pOStack_600;
  BSTR pOStack_5fc;
  int local_5f8;
  undefined4 *puStack_5f4;
  undefined4 *puStack_5f0;
  char *pcStack_5ec;
  int iStack_5e8;
  undefined *puStack_5e4;
  int iStack_5e0;
  undefined *puStack_5dc;
  undefined *puStack_5d8;
  uint *puStack_5d4;
  undefined *puStack_5d0;
  undefined *puStack_5cc;
  undefined *puStack_5c8;
  uint *puStack_5c4;
  int iStack_5c0;
  undefined4 *puStack_5bc;
  undefined4 *puStack_5b8;
  uint *puStack_5b4;
  undefined *puStack_5b0;
  int iStack_5ac;
  undefined *puStack_5a8;
  undefined *puStack_5a4;
  undefined *puStack_5a0;
  byte *pbStack_59c;
  int local_598;
  int local_594;
  int local_590;
  int iStack_58c;
  int iStack_588;
  undefined *puStack_584;
  undefined *puStack_580;
  undefined *puStack_57c;
  undefined *puStack_578;
  undefined *puStack_574;
  int iStack_570;
  undefined *puStack_56c;
  int iStack_568;
  uint *puStack_564;
  undefined *puStack_560;
  char *pcStack_55c;
  undefined *puStack_558;
  undefined *puStack_554;
  undefined *puStack_550;
  undefined *puStack_54c;
  undefined *puStack_548;
  int iStack_544;
  undefined *puStack_540;
  int iStack_53c;
  uint *puStack_538;
  int iStack_534;
  int iStack_530;
  undefined *puStack_52c;
  undefined *puStack_528;
  undefined *puStack_524;
  undefined *puStack_520;
  undefined *puStack_51c;
  int iStack_518;
  undefined *puStack_514;
  int iStack_510;
  uint *puStack_50c;
  undefined *puStack_508;
  char *pcStack_504;
  undefined *puStack_500;
  undefined *puStack_4fc;
  undefined *puStack_4f8;
  undefined *puStack_4f4;
  undefined *puStack_4f0;
  int iStack_4ec;
  undefined *puStack_4e8;
  int iStack_4e4;
  uint *puStack_4e0;
  int iStack_4dc;
  int iStack_4d8;
  int iStack_4d4;
  int iStack_4d0;
  undefined *puStack_4cc;
  int iStack_4c8;
  int iStack_4c4;
  int *local_4c0;
  int *piStack_4bc;
  undefined4 *puStack_4b8;
  int *piStack_4b4;
  int local_4b0;
  uint *puStack_4ac;
  undefined4 *puStack_4a8;
  byte *pbStack_4a4;
  byte *pbStack_4a0;
  undefined *puStack_49c;
  int *local_498;
  int *piStack_494;
  int local_490;
  int local_48c;
  int *piStack_488;
  undefined *local_484;
  int local_480;
  int iStack_47c;
  BSTR pOStack_478;
  int *piStack_474;
  int *piStack_470;
  byte *local_46c;
  undefined *puStack_468;
  byte *pbStack_464;
  byte *pbStack_460;
  byte *pbStack_45c;
  uint *puStack_458;
  undefined4 *puStack_454;
  undefined4 *puStack_450;
  undefined *puStack_44c;
  int iStack_448;
  int iStack_444;
  int iStack_440;
  int iStack_43c;
  undefined *puStack_438;
  undefined *puStack_434;
  undefined *puStack_430;
  undefined *puStack_42c;
  undefined *puStack_428;
  int iStack_424;
  int iStack_420;
  int iStack_41c;
  int iStack_418;
  int iStack_414;
  int iStack_410;
  int iStack_40c;
  int iStack_408;
  byte *local_404;
  byte *pbStack_400;
  byte *pbStack_3fc;
  undefined8 uStack_3f8;
  byte *local_3f0;
  byte *pbStack_3ec;
  byte *pbStack_3e8;
  int iStack_3e4;
  int iStack_3e0;
  byte *pbStack_3dc;
  byte *pbStack_3d8;
  byte *pbStack_3d4;
  float10 fStack_3d0;
  byte *local_3c4;
  int iStack_3c0;
  int iStack_3bc;
  int iStack_3b8;
  byte *pbStack_3b4;
  int iStack_3b0;
  byte *pbStack_3ac;
  int iStack_3a8;
  byte *pbStack_3a4;
  byte *pbStack_3a0;
  int iStack_39c;
  undefined *puStack_398;
  byte *pbStack_394;
  uint *puStack_390;
  int iStack_38c;
  int *local_388;
  int *piStack_384;
  int local_380;
  byte *pbStack_37c;
  uint *puStack_378;
  byte *pbStack_374;
  byte *pbStack_370;
  undefined *puStack_36c;
  byte *pbStack_368;
  byte *pbStack_364;
  byte *pbStack_360;
  undefined4 *puStack_35c;
  uint *puStack_358;
  uint *puStack_354;
  int iStack_350;
  int iStack_34c;
  undefined *puStack_348;
  int iStack_344;
  int *piStack_340;
  undefined *puStack_33c;
  undefined *puStack_338;
  undefined *apuStack_334 [6];
  char acStack_31b [39];
  undefined4 local_2f4;
  int iStack_2f0;
  undefined1 *puStack_2ec;
  char cStack_2e5;
  int *piStack_2e4;
  int *piStack_2e0;
  int *piStack_2dc;
  int *piStack_2d8;
  int *piStack_2d4;
  undefined4 *local_2d0;
  FARPROC pFStack_2cc;
  FARPROC pFStack_2c8;
  HMODULE pHStack_2c4;
  OLECHAR *local_2c0;
  int *piStack_2bc;
  BSTR pOStack_2b8;
  OLECHAR *pOStack_2b4;
  BSTR pOStack_2b0;
  BSTR pOStack_2ac;
  LPCWSTR pWStack_2a8;
  uint *local_2a4;
  HANDLE pvStack_2a0;
  uint uStack_29c;
  int iStack_298;
  uint uStack_294;
  int iStack_290;
  int *piStack_288;
  int *piStack_284;
  byte *pbStack_280;
  bool bStack_279;
  uint *local_278;
  uint *puStack_274;
  undefined *puStack_270;
  int iStack_26c;
  undefined1 *puStack_268;
  int iStack_264;
  undefined1 *puStack_260;
  undefined1 *puStack_25c;
  int iStack_258;
  int local_254 [2];
  undefined4 uStack_24c;
  undefined1 *puStack_248;
  uint *local_144;
  uint *local_140;
  undefined1 *local_13c;
  char *pcStack_138;
  UINT UStack_134;
  undefined1 *puStack_130;
  undefined1 *puStack_12c;
  uint *local_128;
  int iStack_124;
  undefined2 uStack_11e;
  int local_11c;
  int *local_118;
  undefined1 *puStack_114;
  int *piStack_110;
  char acStack_10c [172];
  undefined *puStack_60;
  undefined *puStack_5c;
  uint *puStack_58;
  undefined *puStack_54;
  undefined8 uStack_50;
  int *piVar21;
  undefined2 uVar22;
  undefined2 uVar23;
  undefined **ppuVar24;
  ushort uVar25;
  ushort uVar27;
  byte **ppbVar28;
  int **ppiVar29;
  OLECHAR **ppOVar30;
  BSTR *ppOVar31;
  char *pcVar32;
  char **ppcVar33;
  LPCSTR *ppCVar34;
  undefined8 uVar26;
  uint *puVar35;
  uint **ppuVar36;
  undefined1 **ppuVar37;
  undefined4 **ppuVar38;
  undefined1 *puVar39;
  undefined *local_c;
  int *local_8;
  
                    /* 0x9fbf0  7  UNIFOR */
  puVar6 = &stack0xfffffffc;
  iVar16 = 0x17b;
  do {
    iVar16 = iVar16 + -1;
  } while (iVar16 != 0);
  LOCK();
  UNLOCK();
  local_2f4 = 0;
  puVar5 = (uint *)*in_FS_OFFSET;
  *in_FS_OFFSET = (int)&stack0xffffffd4;
  while ((local_13c = (undefined1 *)FUN_4000b140((char *)param_5), local_13c != (undefined1 *)0x0 &&
         (((param_5 + -1)[(int)local_13c] == 0xd || ((param_5 + -1)[(int)local_13c] == 10))))) {
    (param_5 + -1)[(int)local_13c] = 0;
  }
  *(undefined1 *)*param_4 = 0;
  FUN_40003f78((int *)&local_140);
  FUN_40029500(DAT_400e7214);
  local_118 = (int *)FUN_400031c8((int *)PTR_PTR_40011464,'\x01',extraout_ECX);
  CharUpperBuffA((LPSTR)param_5,1);
  uVar18 = *param_5 - 0x21 == 0x3a;
  switch(*param_5 - 0x21) {
  case 0:
    DAT_400e31f0 = 1;
    break;
  case 2:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    func_0x4009e0c0(local_278,&local_61c);
    FUN_40004010((int *)&local_128,local_61c);
    pcVar12 = FUN_400043cc((undefined *)local_128);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 3:
    FUN_40004140((int *)&puStack_630,(char *)(param_5 + 1));
    FUN_4007a860(puStack_630,(int)auStack_62c);
    FUN_4007a7e4((int)auStack_62c,(int *)&local_128);
    pcVar12 = FUN_400043cc((undefined *)local_128);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 10:
    CharUpperBuffA((LPSTR)(param_5 + 1),1);
    switch(param_5[1]) {
    case 0x2a:
      *(undefined1 *)*param_4 = 0;
      iVar16 = Irbismfn(param_1,(int)param_2);
      IrbisReadGuid(param_1,iVar16,(undefined4 *)acStack_31b);
      if (param_5[2] == 0x31) {
        FUN_40004140((int *)&puStack_668,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(puStack_668,&iStack_664);
        FUN_400041b8(&iStack_66c,acStack_31b,0x27);
        FUN_400042c8((int *)&puStack_660,3);
        pCVar13 = FUN_400043cc(puStack_660);
        pvStack_2a0 = CreateMutexA((LPSECURITY_ATTRIBUTES)0x0,0,pCVar13);
        if (pvStack_2a0 == (HANDLE)0x0) {
          puStack_248 = (undefined1 *)0x0;
        }
        else {
          puStack_248 = (undefined1 *)WaitForSingleObject(pvStack_2a0,1);
          CloseHandle(pvStack_2a0);
          if (puStack_248 == (undefined1 *)0x102) {
            puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
          }
          FUN_4000aa6c(puStack_248,(int *)&puStack_670);
          pcVar12 = FUN_400043cc(puStack_670);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
      }
      else if (acStack_31b[0] != '\0') {
        FUN_40087fc0((int *)param_4,acStack_31b,(uint *)&DAT_400e7210);
      }
      break;
    case 0x2b:
      CharUpperBuffA((LPSTR)(param_5 + 2),1);
      switch(param_5[2]) {
      case 0x30:
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        (**(code **)(*local_118 + 0x40))();
        while (local_128 != (uint *)0x0) {
          puStack_248 = (undefined1 *)FUN_400044f4(",",(char *)local_128);
          if (puStack_248 == (undefined1 *)0x0) {
            iVar16 = FUN_40004208((int)local_128);
            puStack_248 = (undefined1 *)(iVar16 + 1);
          }
          FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),&iStack_bb0);
          (**(code **)(*local_118 + 0x34))(local_118,iStack_bb0);
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
        }
        *(undefined1 *)*param_4 = 0;
        local_13c = (undefined1 *)Irbisnfields(param_1,(int)param_2);
        if (0 < (int)local_13c) {
          puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = local_13c;
          do {
            iStack_124 = Irbisfldtag(param_1,(int)param_2,(int)puStack_248);
            if ((iStack_124 != 0x7fffffff) && (iStack_124 != 0x3b9)) {
              FUN_4000aa6c(iStack_124,&iStack_bb4);
              iVar16 = (**(code **)(*local_118 + 0x50))(local_118,iStack_bb4);
              if (iVar16 < 0) {
                puVar5 = (uint *)0x0;
                pcVar12 = (char *)Irbisfield(param_1,(int)param_2,(int)puStack_248,(char *)0x0);
                FUN_40004140((int *)&local_128,pcVar12);
                while (puStack_114 = (undefined1 *)FUN_400044f4("^",(char *)local_128),
                      puStack_114 != (undefined1 *)0x0) {
                  FUN_40004410((int)local_128,1,(uint)(puStack_114 + -1),&iStack_bb8);
                  ppuVar36 = &puStack_bbc;
                  uVar11 = FUN_40004208((int)local_128);
                  FUN_40004410((int)local_128,(int)(puStack_114 + 2),uVar11,(int *)ppuVar36);
                  puVar5 = puStack_bbc;
                  FUN_400042c8((int *)&local_128,3);
                }
                FUN_40004254((int *)&puStack_bc0,local_128,(undefined4 *)&DAT_400adc24);
                pcVar12 = FUN_400043cc(puStack_bc0);
                FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
              }
            }
            puStack_248 = puStack_248 + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
          puStack_2ec = (undefined1 *)0x0;
        }
        break;
      case 0x31:
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        FUN_40021570((undefined *)local_128,&pOStack_2ac);
        FUN_40003f78((int *)&local_2a4);
        puVar6 = (undefined1 *)FUN_4000482c((int)pOStack_2ac);
        if (0 < (int)puVar6) {
          local_13c = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = puVar6;
          do {
            FUN_40004210((int *)&local_2a4,(undefined4 *)&DAT_400adf30);
            FUN_4000aad0((uint)(ushort)pOStack_2ac[(int)(local_13c + -1)],4,(int *)&puStack_bac);
            FUN_40004210((int *)&local_2a4,puStack_bac);
            local_13c = local_13c + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        pcVar12 = FUN_400043cc((undefined *)local_2a4);
        FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x40:
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        FUN_4009eb58((char *)local_128,&local_be4,extraout_ECX_92,(int)&stack0xfffffffc);
        FUN_40004010((int *)&local_128,local_be4);
        pcVar12 = FUN_400043cc((undefined *)local_128);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x41:
        FUN_40004140((int *)&puStack_bc4,(char *)(param_5 + 3));
        FUN_40021570(puStack_bc4,&pWStack_2a8);
        FUN_400041d0((int *)&local_128,pWStack_2a8);
        UStack_134 = FUN_4000482c((int)pWStack_2a8);
        puStack_260 = (undefined1 *)0x0;
        local_13c = (undefined1 *)((int)&iRam00000000 + 1);
        while ((int)local_13c <= (int)UStack_134) {
          if (puStack_260 == (undefined1 *)0x0) {
            bVar20 = FUN_400206c0(pWStack_2a8[(int)(local_13c + -1)]);
            uVar18 = !bVar20;
            if (!(bool)uVar18) {
              FUN_40004130((int *)&puStack_bcc,
                           CONCAT22((short)((uint)pWStack_2a8 >> 0x10),
                                    pWStack_2a8[(int)(local_13c + -1)]));
              FUN_4000a8bc(puStack_bcc,(int *)&puStack_bc8);
              puVar35 = puStack_bc8;
              FUN_40004130((int *)&puStack_bd0,
                           CONCAT22((short)((uint)pWStack_2a8 >> 0x10),
                                    pWStack_2a8[(int)(local_13c + -1)]));
              FUN_40004318(puVar35,puStack_bd0);
              if ((bool)uVar18) {
                puStack_260 = (undefined1 *)((int)&iRam00000000 + 1);
                puStack_114 = local_13c;
              }
            }
            local_13c = local_13c + 1;
          }
          else if ((((int)local_13c < 1) || (pWStack_2a8[(int)(local_13c + -1)] != L' ')) ||
                  (pWStack_2a8[(int)(local_13c + -2)] == L' ')) {
            bVar20 = FUN_400206c0(pWStack_2a8[(int)(local_13c + -1)]);
            if ((bVar20) &&
               ((((byte)((char *)((int)local_128 + -1))[(int)local_13c] < 0x80 &&
                 ((byte)((char *)((int)local_128 + -1))[(int)puStack_114] < 0x80)) ||
                ((0x7f < (byte)((char *)((int)local_128 + -1))[(int)local_13c] &&
                 (0x7f < (byte)((char *)((int)local_128 + -1))[(int)puStack_114])))))) {
              puStack_260 = puStack_260 + 1;
              if (3 < (int)puStack_260) break;
              local_13c = local_13c + 1;
            }
            else {
              puStack_260 = (undefined1 *)0x0;
              local_13c = puStack_114 + 1;
            }
          }
          else {
            local_13c = local_13c + 1;
          }
        }
        if (3 < (int)puStack_260) {
          FUN_400049e0((int)pWStack_2a8,(int)puStack_114,UStack_134,(BSTR)&local_bd8);
          FUN_40021554(local_bd8,(int *)&local_bd4);
          pcVar12 = FUN_400043cc(local_bd4);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
        break;
      case 0x42:
        FUN_40004140((int *)&pcStack_bdc,(char *)(param_5 + 3));
        FUN_4009d65c(pcStack_bdc);
        break;
      case 0x43:
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        if (local_13c == (undefined1 *)0x0) {
          iVar16 = FUN_40004208((int)local_128);
          local_13c = (undefined1 *)(iVar16 + 1);
        }
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_278);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        FUN_40089b88(local_278,local_128,&iStack_be0,(int)&stack0xfffffffc);
        FUN_40004010((int *)&local_128,iStack_be0);
        pcVar12 = FUN_400043cc((undefined *)local_128);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
      break;
    case 0x30:
      *(undefined1 *)*param_4 = 0;
      FUN_40087fc0((int *)param_4,"0\r",(uint *)&DAT_400e7210);
      uVar10 = Irbismfn(param_1,(int)param_2);
      FUN_4000aa6c(uVar10,&iStack_6a8);
      uVar10 = func_0x4008941c(param_1,param_2);
      FUN_4000aa6c(uVar10,&iStack_6ac);
      FUN_400042c8((int *)&puStack_6a4,4);
      pcVar12 = FUN_400043cc(puStack_6a4);
      FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      FUN_4000aa6c(*(undefined4 *)(*(int *)(*(int *)(*param_1 + 0x2c) + iStack_6ac * 0x43) + 0x18),
                   &iStack_6b4);
      puVar5 = (uint *)&DAT_400adc24;
      FUN_400042c8((int *)&puStack_6b0,3);
      pcVar12 = FUN_400043cc(puStack_6b0);
      FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      iVar16 = Irbismfn(param_1,iStack_6ac);
      IrbisReadGuid(param_1,iVar16,(undefined4 *)acStack_31b);
      if (acStack_31b[0] != '\0') {
        FUN_4000aa6c(0x7fffffff,&iStack_6bc);
        FUN_400041b8(&iStack_6c0,acStack_31b,0x27);
        puVar5 = (uint *)&DAT_400adc24;
        FUN_400042c8((int *)&puStack_6b8,4);
        pcVar12 = FUN_400043cc(puStack_6b8);
        FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
      local_13c = (undefined1 *)Irbisnfields(param_1,iStack_6ac);
      if (0 < (int)local_13c) {
        puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
        puStack_2ec = local_13c;
        do {
          pcVar12 = (char *)Irbisfield(param_1,iStack_6ac,(int)puStack_248,(char *)0x0);
          FUN_40004140((int *)&local_128,pcVar12);
          iStack_124 = Irbisfldtag(param_1,iStack_6ac,(int)puStack_248);
          FUN_4000aa6c(iStack_124,&iStack_6c8);
          puVar5 = (uint *)&DAT_400adc24;
          FUN_400042c8((int *)&puStack_6c4,4);
          pcVar12 = FUN_400043cc(puStack_6c4);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          puStack_248 = puStack_248 + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
        puStack_2ec = (undefined1 *)0x0;
      }
      break;
    case 0x31:
      CharUpperBuffA((LPSTR)(param_5 + 2),1);
      bVar1 = param_5[2];
      if (bVar1 < 0x50) {
        if (bVar1 != 0x4f) {
          if (bVar1 < 0x4a) {
            if (bVar1 != 0x49) {
              if (bVar1 == 0) {
                (**(code **)(*DAT_400e7224 + 0x40))();
                FUN_400b9308();
                break;
              }
              if (bVar1 == 0x41) {
                FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
                puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
                if (0 < (int)puStack_248) {
                  piVar21 = &iStack_740;
                  uVar11 = FUN_40004208((int)local_128);
                  FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,piVar21);
                  func_0x4009bc1c(iStack_740,&uStack_73c);
                  uVar10 = uStack_73c;
                  FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),&iStack_748);
                  func_0x4009bc1c(iStack_748,&uStack_744);
                  func_0x4009c108(uStack_744,uVar10,&puStack_738);
                  pcVar12 = FUN_400043cc(puStack_738);
                  FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
                }
                break;
              }
              if (bVar1 != 0x47) break;
            }
            FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
            local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_128);
            if (local_13c == (undefined1 *)0x0) {
              FUN_40003f78((int *)&local_144);
            }
            else {
              ppuVar36 = &local_144;
              uVar11 = FUN_40004208((int)local_128);
              FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
              FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_128);
            }
            if (param_5[2] == 0x47) {
              func_0x4009bc1c(local_128,&iStack_74c);
              FUN_40004010((int *)&local_128,iStack_74c);
            }
            FUN_4009c380((int)local_128,(char *)local_144,&puStack_750,&stack0xfffffffc);
            pcVar12 = FUN_400043cc(puStack_750);
            FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
            break;
          }
          if (bVar1 != 0x4b) {
            if (bVar1 == 0x4d) {
              FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
              puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
              if (0 < (int)puStack_248) {
                piVar21 = &iStack_718;
                uVar11 = FUN_40004208((int)local_128);
                FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,piVar21);
                func_0x4009bc1c(iStack_718,&uStack_714);
                uVar10 = uStack_714;
                FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),&iStack_720);
                func_0x4009bc1c(iStack_720,&uStack_71c);
                func_0x4009be44(uStack_71c,uVar10,&puStack_710);
                pcVar12 = FUN_400043cc(puStack_710);
                FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
              }
            }
            break;
          }
        }
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        puStack_248 = (undefined1 *)FUN_400044f4("|",(char *)local_128);
        if (puStack_248 == (undefined1 *)0x0) {
          puStack_248 = (undefined1 *)FUN_400044f4("\\",(char *)local_128);
        }
        if (0 < (int)puStack_248) {
          FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&puStack_274);
          if (param_5[2] == 0x4f) {
            piVar21 = &iStack_6f8;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,piVar21);
            (**(code **)(*local_118 + 0x2c))(local_118,iStack_6f8);
          }
          else {
            piVar21 = &iStack_700;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,piVar21);
            func_0x4009bc1c(iStack_700,&uStack_6fc);
            (**(code **)(*local_118 + 0x2c))(local_118,uStack_6fc);
          }
          FUN_40003f78((int *)&local_128);
          puVar6 = (undefined1 *)(**(code **)(*local_118 + 0x14))();
          if (-1 < (int)(puVar6 + -1)) {
            local_13c = (undefined1 *)0x0;
            puStack_2ec = puVar6;
            do {
              (**(code **)(*local_118 + 0xc))(local_118,local_13c,auStack_70c);
              FUN_400042c8(&iStack_708,3);
              func_0x4008e5ac(iStack_708,1,&puStack_704);
              FUN_40004210((int *)&local_128,puStack_704);
              iVar16 = (**(code **)(*local_118 + 0x14))();
              if ((int)local_13c < iVar16 + -1) {
                FUN_40004210((int *)&local_128,(undefined4 *)&DAT_400adc24);
              }
              local_13c = local_13c + 1;
              puStack_2ec = puStack_2ec + -1;
            } while (puStack_2ec != (undefined1 *)0x0);
          }
          pcVar12 = FUN_400043cc((undefined *)local_128);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
      }
      else {
        switch(bVar1) {
        case 0x52:
          FUN_40004140(&iStack_6d0,(char *)(param_5 + 3));
          func_0x4009bc1c(iStack_6d0,&puStack_6cc);
          pcVar12 = FUN_400043cc(puStack_6cc);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          break;
        case 0x53:
          FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
          puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
          if (0 < (int)puStack_248) {
            piVar21 = &iStack_72c;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,piVar21);
            func_0x4009bc1c(iStack_72c,&uStack_728);
            uVar10 = uStack_728;
            FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),&local_734);
            func_0x4009bc1c(local_734,&uStack_730);
            func_0x4009bfa4(uStack_730,uVar10,&puStack_724);
            pcVar12 = FUN_400043cc(puStack_724);
            FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          }
          break;
        case 0x54:
        case 0x56:
          FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
          if (param_5[2] == 0x54) {
            func_0x4009bc1c(local_128,&iStack_754);
            FUN_40004010((int *)&local_128,iStack_754);
          }
          FUN_4009c274((undefined *)local_128,'\0',(int *)&puStack_758);
          pcVar12 = FUN_400043cc(puStack_758);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          break;
        case 0x57:
          FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
          puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
          if (0 < (int)puStack_248) {
            FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pcStack_6d4);
            puStack_114 = (undefined1 *)FUN_400044f4(",",pcStack_6d4);
            if (puStack_114 == (undefined1 *)0x0) {
              puStack_12c = (undefined1 *)0xffffffff;
            }
            else {
              FUN_40004410((int)local_128,(int)(puStack_114 + 1),
                           (uint)(puStack_248 + (-1 - (int)puStack_114)),(int *)&pbStack_6d8);
              puStack_12c = (undefined1 *)FUN_4000ab48(pbStack_6d8,0,extraout_ECX_46);
              ppuVar38 = &puStack_6dc;
              uVar11 = FUN_40004208((int)local_128);
              FUN_40004410((int)local_128,(int)puStack_248,uVar11,(int *)ppuVar38);
              FUN_40004410((int)local_128,1,(uint)(puStack_114 + -1),(int *)&puStack_6e0);
              FUN_40004254((int *)&local_128,puStack_6e0,puStack_6dc);
              puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
            }
            if (((int)puStack_248 < 2) || ((char)*local_128 != '*')) {
              FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_6ec);
              local_13c = (undefined1 *)FUN_4000ab48(pbStack_6ec,0xffffffff,extraout_ECX_49);
            }
            else if ((int)puStack_248 < 3) {
              local_13c = param_6;
            }
            else if (*(char *)((int)local_128 + 1) == '+') {
              FUN_40004410((int)local_128,3,(uint)(puStack_248 + -3),(int *)&pbStack_6e4);
              iVar16 = FUN_4000ab48(pbStack_6e4,0,extraout_ECX_47);
              local_13c = param_6 + iVar16;
            }
            else if (*(char *)((int)local_128 + 1) == '-') {
              FUN_40004410((int)local_128,3,(uint)(puStack_248 + -3),(int *)&pbStack_6e8);
              iVar16 = FUN_4000ab48(pbStack_6e8,0,extraout_ECX_48);
              local_13c = param_6 + -iVar16;
            }
            else {
              local_13c = param_6;
            }
            if (-1 < (int)local_13c) {
              ppuVar36 = &local_128;
              uVar11 = FUN_40004208((int)local_128);
              uVar18 = puStack_248 + 1 == (undefined1 *)0x0;
              FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
              FUN_40004318(local_128,(uint *)&DAT_400ad760);
              if ((bool)uVar18) {
                FUN_4000aa6c(param_6,(int *)&local_128);
              }
              iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
              if (iVar16 <= (int)local_13c) {
                iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
                if (-1 < (int)local_13c - iVar16) {
                  puStack_2ec = (undefined1 *)(((int)local_13c - iVar16) + 1);
                  puStack_248 = (undefined1 *)0x0;
                  do {
                    (**(code **)(*DAT_400e7224 + 0x34))(DAT_400e7224,0);
                    puStack_248 = puStack_248 + 1;
                    puStack_2ec = puStack_2ec + -1;
                  } while (puStack_2ec != (undefined1 *)0x0);
                }
              }
              if ((int)puStack_12c < 0) {
                (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
                FUN_400b9414((int)local_13c,(int)local_128);
              }
              else {
                (**(code **)(*local_118 + 0x2c))(local_118,local_128);
                iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
                if (iVar16 <= (int)puStack_12c) {
                  iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
                  if (-1 < (int)puStack_12c - iVar16) {
                    puStack_2ec = (undefined1 *)(((int)puStack_12c - iVar16) + 1);
                    puStack_248 = (undefined1 *)0x0;
                    do {
                      (**(code **)(*DAT_400e7224 + 0x34))(DAT_400e7224,0);
                      puStack_248 = puStack_248 + 1;
                      puStack_2ec = puStack_2ec + -1;
                    } while (puStack_2ec != (undefined1 *)0x0);
                  }
                }
                iVar16 = (**(code **)(*local_118 + 0x14))();
                puVar6 = local_13c + iVar16 + -1;
                iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
                if (iVar16 <= (int)puVar6) {
                  iVar16 = (**(code **)(*local_118 + 0x14))();
                  puVar6 = local_13c;
                  iVar3 = (**(code **)(*DAT_400e7224 + 0x14))();
                  if (-1 < (int)(puVar6 + ((iVar16 + -1) - iVar3))) {
                    puStack_2ec = puVar6 + ((iVar16 + -1) - iVar3) + 1;
                    puStack_248 = (undefined1 *)0x0;
                    do {
                      (**(code **)(*DAT_400e7224 + 0x34))(DAT_400e7224,0);
                      puStack_248 = puStack_248 + 1;
                      puStack_2ec = puStack_2ec + -1;
                    } while (puStack_2ec != (undefined1 *)0x0);
                  }
                }
                puVar6 = (undefined1 *)(**(code **)(*local_118 + 0x14))();
                if (-1 < (int)(puVar6 + -1)) {
                  puStack_248 = (undefined1 *)0x0;
                  puStack_2ec = puVar6;
                  do {
                    (**(code **)(*local_118 + 0xc))(local_118,puStack_248,&uStack_6f0);
                    (**(code **)(*DAT_400e7224 + 0x20))
                              (DAT_400e7224,local_13c + (int)puStack_248,uStack_6f0);
                    puStack_248 = puStack_248 + 1;
                    puStack_2ec = puStack_2ec + -1;
                  } while (puStack_2ec != (undefined1 *)0x0);
                }
                uVar10 = (**(code **)(*local_118 + 0x14))();
                FUN_4000aa6c(uVar10,&iStack_6f4);
                (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,puStack_12c,iStack_6f4);
                FUN_400b9308();
              }
            }
          }
        }
      }
      break;
    case 0x32:
      FUN_400b912c((LPSTR)(param_5 + 2),1,0);
      break;
    case 0x33:
      CharUpperBuffA((LPSTR)(param_5 + 2),1);
      switch(param_5[2]) {
      case 0x2b:
        FUN_40087f50((int *)param_4,(char *)(param_5 + 3),(uint *)&DAT_400e7210);
        FUN_40003f78((int *)&local_128);
        puVar6 = (undefined1 *)FUN_4000b140((char *)*param_4);
        if (-1 < (int)(puVar6 + -1)) {
          local_13c = (undefined1 *)0x0;
          puStack_2ec = puVar6;
          do {
            if (local_13c[*param_4] == '+') {
              FUN_40004210((int *)&local_128,(undefined4 *)&UNK_400adcc8);
            }
            else {
              FUN_40004120((int *)&puStack_858,CONCAT31((int3)(*param_4 >> 8),local_13c[*param_4]));
              FUN_40004210((int *)&local_128,puStack_858);
            }
            local_13c = local_13c + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        pcVar12 = FUN_400043cc((undefined *)local_128);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x41:
        *(undefined1 *)*param_4 = 0;
        local_13c = (undefined1 *)Irbisnfields(param_1,(int)param_2);
        if (0 < (int)local_13c) {
          puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = local_13c;
          do {
            pcVar12 = (char *)Irbisfield(param_1,(int)param_2,(int)puStack_248,(char *)0x0);
            FUN_40004140((int *)&local_128,pcVar12);
            iStack_124 = Irbisfldtag(param_1,(int)param_2,(int)puStack_248);
            FUN_4000aa6c(iStack_124,&iStack_868);
            puVar5 = (uint *)&DAT_400adc24;
            FUN_400042c8((int *)&puStack_864,4);
            pcVar12 = FUN_400043cc(puStack_864);
            FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
            puStack_248 = puStack_248 + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
          puStack_2ec = (undefined1 *)0x0;
        }
        break;
      case 0x43:
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        iVar16 = FUN_400044f4("__",(char *)local_128);
        if (iVar16 < 1) {
          FUN_400235ec(local_128,0xfd,(int *)&puStack_860);
          pcVar12 = FUN_400043cc(puStack_860);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
        else {
          ppuVar36 = &local_2a4;
          iVar16 = FUN_400044f4("__",(char *)local_128);
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,iVar16,uVar11,(int *)ppuVar36);
          ppuVar36 = &local_128;
          iVar16 = FUN_400044f4("__",(char *)local_128);
          FUN_40004410((int)local_128,1,iVar16 - 1,(int *)ppuVar36);
          iVar16 = FUN_40004208((int)local_2a4);
          FUN_400235ec(local_128,0xf9 - iVar16,&iStack_85c);
          FUN_40004010((int *)&local_128,iStack_85c);
          FUN_40004210((int *)&local_128,local_2a4);
          pcVar12 = FUN_400043cc((undefined *)local_128);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
        break;
      case 0x44:
        FUN_40004140(&iStack_82c,(char *)(param_5 + 3));
        FUN_400232a8(iStack_82c,(int *)&puStack_828);
        pcVar12 = FUN_400043cc(puStack_828);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x45:
        FUN_40004140(&iStack_824,(char *)(param_5 + 3));
        FUN_4002312c(iStack_824,(int *)&puStack_820);
        pcVar12 = FUN_400043cc(puStack_820);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x46:
        func_0x4008d1bc();
        break;
      case 0x47:
        func_0x4008c420();
        break;
      case 0x48:
        FUN_40004140(&iStack_834,(char *)(param_5 + 3));
        func_0x4002705c(iStack_834,&puStack_830);
        pcVar12 = FUN_400043cc(puStack_830);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x4a:
        FUN_40003f78((int *)&local_140);
        FUN_40004140((int *)&local_278,(char *)(param_5 + 3));
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_278);
        if (0 < (int)local_13c) {
          FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&puStack_274);
          if (puStack_274 == (uint *)0x0) {
            FUN_40004140((int *)&puStack_7f0,*(char **)((int)param_1 + 0x7da));
            FUN_4000afc4(puStack_7f0,(int *)&puStack_274);
          }
          if ((puStack_274 == (uint *)0x0) || ((char)*puStack_274 != '+')) {
            cStack_2e5 = '\0';
          }
          else {
            ppuVar36 = &puStack_274;
            iVar16 = FUN_40004208((int)puStack_274);
            FUN_40004410((int)puStack_274,2,iVar16 - 1,(int *)ppuVar36);
            cStack_2e5 = '\x01';
            if (puStack_274 == (uint *)0x0) {
              FUN_40004140((int *)&puStack_7f4,*(char **)((int)param_1 + 0x7da));
              FUN_4000afc4(puStack_7f4,(int *)&puStack_274);
            }
          }
          ppuVar36 = &local_144;
          uVar11 = FUN_40004208((int)local_278);
          FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
          uVar19 = 1;
          puStack_260 = (undefined1 *)0x0;
          ppuVar36 = &puStack_7f8;
          iVar16 = FUN_40004208((int)local_144);
          FUN_40004410((int)local_144,iVar16,1,(int *)ppuVar36);
          FUN_40004318(puStack_7f8,(uint *)&UNK_400adcb8);
          uVar18 = 0;
          if ((bool)uVar19) {
            puStack_260 = (undefined1 *)((int)&iRam00000000 + 1);
            ppuVar36 = &local_144;
            iVar16 = FUN_40004208((int)local_144);
            uVar18 = iVar16 - 1U == 0;
            FUN_40004410((int)local_144,1,iVar16 - 1U,(int *)ppuVar36);
          }
          pcVar12 = FUN_400043cc((undefined *)local_144);
          pcVar12 = (char *)FUN_400252c0(pcVar12,&DAT_400e6ec8);
          FUN_40004140((int *)&local_144,pcVar12);
          FUN_40004140((int *)&puStack_804,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_804,(int *)&pbStack_800);
          FUN_4000a77c(pbStack_800,(int *)&puStack_7fc);
          FUN_4000a77c((byte *)puStack_274,(int *)&puStack_808);
          FUN_40004318(puStack_7fc,puStack_808);
          piStack_110 = param_1;
          if (!(bool)uVar18 || cStack_2e5 != '\0') {
            piStack_110 = Irbisinit();
            FUN_40089484((int *)&puStack_274,DAT_400e7214);
            if (cStack_2e5 == '\0') {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7214,1);
              FUN_40004140((int *)&puStack_814,pcVar12);
              FUN_40004210((int *)&puStack_814,puStack_274);
              pcVar12 = FUN_400043cc(puStack_814);
              local_13c = (undefined1 *)Irbisinitterm((int)piStack_110,pcVar12);
            }
            else {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7214,1);
              FUN_40004140(&iStack_810,pcVar12);
              FUN_400042c8((int *)&puStack_80c,3);
              pcVar12 = FUN_400043cc(puStack_80c);
              local_13c = (undefined1 *)Irbisinitterm((int)piStack_110,pcVar12);
            }
            if (local_13c != (undefined1 *)0x0) {
              FUN_40003f78((int *)&puStack_274);
            }
          }
          if (puStack_274 != (uint *)0x0) {
            FUN_400235ec(local_144,0xfe,&iStack_818);
            FUN_40004010((int *)&local_144,iStack_818);
            pcVar12 = FUN_400043cc((undefined *)local_144);
            FUN_4000b1d0(acStack_10c,pcVar12,0xfe);
            local_13c = (undefined1 *)Irbisfind((int)piStack_110,acStack_10c);
            puStack_268 = (undefined1 *)0x0;
            if (local_13c == (undefined1 *)0x0) {
code_r0x400a78c9:
              puStack_268 = (undefined1 *)Irbisnposts((int)piStack_110);
              puStack_248 = puStack_268;
              if (puStack_260 == (undefined1 *)((int)&iRam00000000 + 1)) {
                while (local_13c = (undefined1 *)Irbisnxtterm((int)piStack_110,acStack_10c),
                      local_13c != (undefined1 *)0xfffffe6f) {
                  iVar16 = FUN_40004208((int)local_144);
                  pcVar12 = FUN_400043cc((undefined *)local_144);
                  iVar16 = FUN_4000b2ec(pcVar12,acStack_10c,iVar16);
                  if ((iVar16 != 0) || (local_13c == (undefined1 *)0xffffff35)) break;
                  puStack_248 = (undefined1 *)Irbisnposts((int)piStack_110);
                  puStack_268 = puStack_268 + (int)puStack_248;
                }
              }
            }
            else {
              iVar16 = FUN_40004208((int)local_144);
              pcVar12 = FUN_400043cc((undefined *)local_144);
              iVar16 = FUN_4000b2ec(pcVar12,acStack_10c,iVar16);
              if (iVar16 == 0) goto code_r0x400a78c9;
            }
            if (-1 < (int)puStack_268) {
              FUN_4000aa6c(puStack_268,(int *)&local_140);
            }
          }
          if (piStack_110 != param_1) {
            Irbisclose(piStack_110);
          }
        }
        pcVar12 = FUN_400043cc((undefined *)local_140);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x53:
        func_0x4008c4ac();
        break;
      case 0x54:
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        if ((int)local_13c < 1) {
          FUN_40087f50((int *)param_4,"0",(uint *)&DAT_400e7210);
        }
        else {
          FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_2a4);
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
          FUN_400882d8(local_2a4,&local_13c);
          fStack_3d0 = in_ST0;
          FUN_400882d8(local_128,&local_13c);
          FUN_40002cf0();
          func_0x4000aa9c(&iStack_81c);
          FUN_40004010((int *)&local_128,iStack_81c);
          pcVar12 = FUN_400043cc((undefined *)local_128);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
        break;
      case 0x55:
        FUN_40004140((int *)&puStack_83c,(char *)(param_5 + 3));
        FUN_40023740(puStack_83c,(int *)&puStack_838);
        pcVar12 = FUN_400043cc(puStack_838);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        break;
      case 0x57:
        FUN_40004140((int *)&puStack_848,(char *)(param_5 + 3));
        FUN_40021570(puStack_848,&local_844);
        FUN_40021554((int *)local_844,&local_840);
        if (local_840 == 0) {
          FUN_40004140((int *)&puStack_854,(char *)(param_5 + 3));
          pcVar12 = FUN_400043cc(puStack_854);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
        else {
          FUN_40004140((int *)&puStack_850,(char *)(param_5 + 3));
          FUN_400237a8(puStack_850,(int *)&puStack_84c);
          pcVar12 = FUN_400043cc(puStack_84c);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
      }
      break;
    case 0x34:
      FUN_40004140((int *)&pbStack_86c,(char *)(param_5 + 2));
      FUN_4000a77c(pbStack_86c,(int *)&local_128);
      local_13c = (undefined1 *)Irbisnfields(param_1,0);
      iVar16 = FUN_40004208((int)local_128);
      if ((1 < iVar16) && ((int)param_6 <= (int)local_13c)) {
        (**(code **)(*local_118 + 0x40))();
        uVar18 = local_13c == (undefined1 *)0x0;
        if (0 < (int)local_13c) {
          puStack_2ec = local_13c;
          puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
          do {
            Irbisfldtag(param_1,0,(int)puStack_114);
            FUN_4000aa6c(puStack_114,&iStack_874);
            pcVar12 = (char *)Irbisfield(param_1,0,(int)puStack_114,"");
            FUN_40004140(&iStack_878,pcVar12);
            iVar16 = iStack_878;
            FUN_400042c8(&iStack_870,3);
            (**(code **)(*local_118 + 0x38))(local_118,iStack_870,iVar16);
            puStack_114 = puStack_114 + 1;
            puStack_2ec = puStack_2ec + -1;
            uVar18 = puStack_2ec == (undefined1 *)0x0;
          } while (!(bool)uVar18);
        }
        FUN_40004410((int)local_128,2,1,(int *)&puStack_87c);
        FUN_40004318(puStack_87c,(uint *)&DAT_400adb24);
        if ((bool)uVar18) {
          FUN_40023098(local_118);
        }
        local_13c = param_6;
        uVar18 = param_6 == (undefined1 *)0x0;
        if ((bool)uVar18) {
          local_13c = (undefined1 *)((int)&iRam00000000 + 1);
        }
        FUN_40003f78((int *)&local_144);
        FUN_40004410((int)local_128,1,1,(int *)&puStack_880);
        FUN_40004318(puStack_880,(uint *)&UNK_400adcec);
        uVar19 = 0;
        if ((bool)uVar18) {
          uVar19 = local_13c == (undefined1 *)((int)&iRam00000000 + 1);
          uVar10 = (**(code **)(*local_118 + 0x18))();
          FUN_4000aa6c(uVar10,(int *)&local_144);
        }
        FUN_40004410((int)local_128,1,1,(int *)&puStack_884);
        FUN_40004318(puStack_884,(uint *)&UNK_400adcf8);
        uVar18 = 0;
        if ((bool)uVar19) {
          ppuVar36 = &local_144;
          (**(code **)(*local_118 + 0xc))(local_118,local_13c + -1,&iStack_888);
          uVar11 = FUN_40004208(iStack_888);
          (**(code **)(*local_118 + 0xc))(local_118,local_13c + -1,&pcStack_88c);
          iVar16 = FUN_400044f4("_",pcStack_88c);
          iVar16 = iVar16 + 1;
          uVar18 = local_13c + -1 == (undefined1 *)0x0;
          (**(code **)(*local_118 + 0xc))(local_118,local_13c + -1,&iStack_890);
          FUN_40004410(iStack_890,iVar16,uVar11,(int *)ppuVar36);
        }
        FUN_40004410((int)local_128,1,1,(int *)&puStack_894);
        FUN_40004318(puStack_894,(uint *)&UNK_400add04);
        if ((bool)uVar18) {
          ppuVar36 = &local_144;
          (**(code **)(*local_118 + 0xc))(local_118,local_13c + -1,&pcStack_898);
          iVar16 = FUN_400044f4("_",pcStack_898);
          uVar11 = iVar16 - 1;
          (**(code **)(*local_118 + 0xc))(local_118,local_13c + -1,&iStack_89c);
          FUN_40004410(iStack_89c,1,uVar11,(int *)ppuVar36);
        }
        pcVar12 = FUN_400043cc((undefined *)local_144);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
      break;
    case 0x35:
      FUN_40004140((int *)&pbStack_8a0,(char *)(param_5 + 2));
      FUN_4000a77c(pbStack_8a0,(int *)&local_128);
      if (DAT_400e71cc == (int *)0x0) {
        uVar10 = (**(code **)(iRam00000000 + 8))(0,&DAT_400adb78,"DepositPriority");
        uVar26 = CONCAT44(uVar10,local_118);
        FUN_40004140((int *)&puStack_8bc,*(char **)((int)param_1 + 0x7da));
        FUN_4000aea0(puStack_8bc,(int *)&local_8b8);
        ppuVar24 = &local_8b8;
        ppuVar38 = &puStack_8c0;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar38);
        FUN_40004210((int *)ppuVar24,puStack_8c0);
        FUN_40004140((int *)&local_8c8,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(local_8c8,(int *)&puStack_8c4);
        FUN_400267fc(puStack_8c4,local_8b8,DAT_400e71f8,(int *)uVar26,
                     (char)((ulonglong)uVar26 >> 0x20));
      }
      else {
        uVar26 = CONCAT44(1,local_118);
        FUN_40004140((int *)&puStack_8a8,*(char **)((int)param_1 + 0x7da));
        FUN_4000aea0(puStack_8a8,(int *)&puStack_8a4);
        ppuVar24 = &puStack_8a4;
        ppuVar38 = &puStack_8ac;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar38);
        FUN_40004210((int *)ppuVar24,puStack_8ac);
        FUN_40004140((int *)&local_8b4,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(local_8b4,(int *)&puStack_8b0);
        FUN_400267fc(puStack_8b0,puStack_8a4,DAT_400e71f8,(int *)uVar26,
                     (char)((ulonglong)uVar26 >> 0x20));
      }
      local_13c = param_6;
      if (param_6 == (undefined1 *)0x0) {
        local_13c = (undefined1 *)((int)&iRam00000000 + 1);
      }
      iVar16 = FUN_400044f4(".MNU",(char *)local_128);
      if (iVar16 < 1) {
        puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
      }
      else {
        puStack_114 = (undefined1 *)((int)&iRam00000000 + 2);
      }
      iVar16 = (**(code **)(*local_118 + 0x14))();
      uVar18 = (undefined1 *)(iVar16 / (int)puStack_114) == local_13c;
      if ((int)local_13c <= iVar16 / (int)puStack_114) {
        FUN_40003f78((int *)&local_144);
        FUN_40004410((int)local_128,1,1,(int *)&puStack_8cc);
        FUN_40004318(puStack_8cc,(uint *)&UNK_400adcec);
        uVar19 = 0;
        if ((bool)uVar18) {
          uVar19 = local_13c + -1 == (undefined1 *)0x0;
          (**(code **)(*local_118 + 0xc))
                    (local_118,(int)(local_13c + -1) * (int)puStack_114,&puStack_8d0);
          FUN_40023740(puStack_8d0,(int *)&local_144);
          func_0x40087e50(local_144,&iStack_8d4);
          FUN_40004010((int *)&local_144,iStack_8d4);
        }
        FUN_40004410((int)local_128,1,1,(int *)&puStack_8d8);
        FUN_40004318(puStack_8d8,(uint *)&UNK_400adcf8);
        if ((bool)uVar19) {
          (**(code **)(*local_118 + 0xc))
                    (local_118,(int)puStack_114 * (int)local_13c + -1,&puStack_8dc);
          FUN_40023740(puStack_8dc,(int *)&local_144);
        }
        pcVar12 = FUN_400043cc((undefined *)local_144);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
      break;
    case 0x36:
      FUN_40004140((int *)&pbStack_8e0,(char *)(param_5 + 2));
      local_13c = (undefined1 *)FUN_4000ab48(pbStack_8e0,0,extraout_ECX_67);
      if (local_13c == (undefined1 *)0x0) {
        uVar11 = IrbisIsDeleted(param_1,0);
        if ((char)uVar11 == '\0') {
          FUN_40087f50((int *)param_4,"1",(uint *)&DAT_400e7210);
        }
        else {
          FUN_40087f50((int *)param_4,"0",(uint *)&DAT_400e7210);
        }
      }
      else if (local_13c == (undefined1 *)((int)&iRam00000000 + 1)) {
        uVar11 = IrbisIsActualized(param_1,0);
        if ((char)uVar11 == '\0') {
          FUN_40087f50((int *)param_4,"1",(uint *)&DAT_400e7210);
        }
        else {
          FUN_40087f50((int *)param_4,"0",(uint *)&DAT_400e7210);
        }
      }
      else if (local_13c == (undefined1 *)((int)&iRam00000000 + 2)) {
        uVar11 = IrbisIsLocked(param_1,0);
        if ((char)uVar11 == '\0') {
          FUN_40087f50((int *)param_4,"1",(uint *)&DAT_400e7210);
        }
        else {
          FUN_40087f50((int *)param_4,"0",(uint *)&DAT_400e7210);
        }
      }
      else if (local_13c == (undefined1 *)((int)&iRam00000000 + 3)) {
        bVar20 = IrbisIsActualizedFT(param_1,0);
        if (bVar20) {
          FUN_40087f50((int *)param_4,"0",(uint *)&DAT_400e7210);
        }
        else {
          FUN_40087f50((int *)param_4,"1",(uint *)&DAT_400e7210);
        }
      }
      break;
    case 0x37:
      CharUpperBuffA((LPSTR)(param_5 + 2),1);
      bVar1 = param_5[2];
      if (bVar1 < 0x53) {
        if (bVar1 == 0x52) {
          FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
          puStack_248 = (undefined1 *)FUN_400044f4(",",(char *)local_128);
          if (puStack_248 == (undefined1 *)0x0) {
            iVar16 = FUN_40004208((int)local_128);
            puStack_248 = (undefined1 *)(iVar16 + 1);
          }
          FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_75c);
          local_13c = (undefined1 *)FUN_4000ab48(pbStack_75c,0xffffffff,extraout_ECX_50);
          if (((-1 < (int)local_13c) &&
              (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16)) &&
             ((**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&iStack_760),
             iStack_760 != 0)) {
            ppuVar36 = &local_128;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
            if (local_128 == (uint *)0x0) {
              puStack_12c = param_6;
            }
            else {
              puStack_12c = (undefined1 *)FUN_4000ab48((byte *)local_128,0xffffffff,extraout_ECX_51)
              ;
            }
            if (puStack_12c == (undefined1 *)0x0) {
              (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&local_128);
            }
            else {
              (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&uStack_764);
              (**(code **)(*local_118 + 0x2c))(local_118,uStack_764);
              if (puStack_12c == (undefined1 *)0xffffffff) {
                iVar16 = (**(code **)(*local_118 + 0x14))();
                (**(code **)(*local_118 + 0xc))(local_118,iVar16 + -1,&local_128);
              }
              else {
                iVar16 = (**(code **)(*local_118 + 0x14))();
                if (iVar16 < (int)puStack_12c) {
                  FUN_40003f78((int *)&local_128);
                }
                else {
                  (**(code **)(*local_118 + 0xc))(local_118,puStack_12c + -1,&local_128);
                }
              }
            }
            pcVar12 = FUN_400043cc((undefined *)local_128);
            FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          }
        }
        else if (bVar1 < 0x48) {
          if (bVar1 == 0x47) {
            FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
            local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_128);
            if (local_13c == (undefined1 *)0x0) {
              FUN_40003f78((int *)&local_144);
              iVar16 = extraout_ECX_61;
            }
            else {
              ppuVar36 = &local_144;
              uVar11 = FUN_40004208((int)local_128);
              FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
              FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_128);
              iVar16 = extraout_ECX_62;
            }
            local_13c = (undefined1 *)FUN_4000ab48((byte *)local_128,0xffffffff,iVar16);
            if ((-1 < (int)local_13c) &&
               (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16)) {
              (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&iStack_7c4);
              FUN_4009c380(iStack_7c4,(char *)local_144,&iStack_7c0,puVar6);
              FUN_40004010((int *)&local_128,iStack_7c0);
              (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
              FUN_400b9414((int)local_13c,(int)local_128);
            }
          }
          else if (bVar1 == 0) {
            (**(code **)(*DAT_400e7224 + 0x40))();
            FUN_400b9308();
          }
          else if (bVar1 == 0x41) {
            FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
            puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
            if (0 < (int)puStack_248) {
              FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_7ac);
              local_13c = (undefined1 *)FUN_4000ab48(pbStack_7ac,0xffffffff,extraout_ECX_59);
              ppbVar28 = &pbStack_7b0;
              uVar11 = FUN_40004208((int)local_128);
              FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppbVar28);
              puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_7b0,0xffffffff,extraout_ECX_60);
              if (((-1 < (int)local_13c) && (-1 < (int)puStack_114)) &&
                 ((iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16 &&
                  (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)puStack_114 < iVar16)))) {
                (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,puStack_114,&uStack_7b8);
                (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&uStack_7bc);
                func_0x4009c108(uStack_7bc,uStack_7b8,&iStack_7b4);
                FUN_40004010((int *)&local_128,iStack_7b4);
                (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
                FUN_400b9414((int)local_13c,(int)local_128);
              }
            }
          }
        }
        else if (bVar1 == 0x49) {
          FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
          puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
          if ((0 < (int)puStack_248) &&
             (puVar6 = (undefined1 *)FUN_40004208((int)local_128), puVar6 != puStack_248)) {
            FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_7d4);
            local_13c = (undefined1 *)FUN_4000ab48(pbStack_7d4,0xffffffff,extraout_ECX_66);
            if ((-1 < (int)local_13c) &&
               ((iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16 &&
                ((**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&iStack_7d8),
                iStack_7d8 != 0)))) {
              ppuVar24 = &puStack_7e0;
              uVar11 = FUN_40004208((int)local_128);
              FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppuVar24);
              FUN_40026f28(puStack_7e0,&iStack_7dc);
              FUN_40004010((int *)&local_128,iStack_7dc);
              (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&puStack_7e8);
              FUN_40026f28(puStack_7e8,&iStack_7e4);
              (**(code **)(*local_118 + 0x2c))(local_118,iStack_7e4);
              local_13c = (undefined1 *)(**(code **)(*local_118 + 0x50))(local_118,local_128);
              if (-1 < (int)local_13c) {
                FUN_4000aa6c(local_13c + 1,(int *)&puStack_7ec);
                pcVar12 = FUN_400043cc(puStack_7ec);
                FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
              }
            }
          }
        }
        else if (bVar1 == 0x4d) {
          FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
          puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
          if (0 < (int)puStack_248) {
            FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_784);
            local_13c = (undefined1 *)FUN_4000ab48(pbStack_784,0xffffffff,extraout_ECX_55);
            ppbVar28 = &pbStack_788;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppbVar28);
            puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_788,0xffffffff,extraout_ECX_56);
            if ((((-1 < (int)local_13c) && (-1 < (int)puStack_114)) &&
                (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16)) &&
               (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)puStack_114 < iVar16)) {
              (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,puStack_114,&uStack_790);
              (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&uStack_794);
              func_0x4009be44(uStack_794,uStack_790,&iStack_78c);
              FUN_40004010((int *)&local_128,iStack_78c);
              (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
              FUN_400b9414((int)local_13c,(int)local_128);
            }
          }
        }
      }
      else if (bVar1 == 0x53) {
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        if (0 < (int)puStack_248) {
          FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_798);
          local_13c = (undefined1 *)FUN_4000ab48(pbStack_798,0xffffffff,extraout_ECX_57);
          ppbVar28 = &pbStack_79c;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppbVar28);
          puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_79c,0xffffffff,extraout_ECX_58);
          if ((((-1 < (int)local_13c) && (-1 < (int)puStack_114)) &&
              (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16)) &&
             (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)puStack_114 < iVar16)) {
            (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,puStack_114,&uStack_7a4);
            (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&uStack_7a8);
            func_0x4009bfa4(uStack_7a8,uStack_7a4,&iStack_7a0);
            FUN_40004010((int *)&local_128,iStack_7a0);
            (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
            FUN_400b9414((int)local_13c,(int)local_128);
          }
        }
      }
      else if (bVar1 == 0x54) {
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        puStack_114 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        iVar16 = extraout_ECX_63;
        if (puStack_114 != (undefined1 *)0x0) {
          ppbVar28 = &pbStack_7c8;
          local_13c = puStack_114;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(puStack_114 + 1),uVar11,(int *)ppbVar28);
          puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_7c8,0,extraout_ECX_64);
          FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_128);
          iVar16 = extraout_ECX_65;
        }
        local_13c = (undefined1 *)FUN_4000ab48((byte *)local_128,0xffffffff,iVar16);
        if ((-1 < (int)local_13c) &&
           (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), (int)local_13c < iVar16)) {
          (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&puStack_7d0);
          FUN_4009c274(puStack_7d0,(char)puStack_114,&iStack_7cc);
          FUN_40004010((int *)&local_128,iStack_7cc);
          (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
          FUN_400b9414((int)local_13c,(int)local_128);
        }
      }
      else if (bVar1 == 0x55) {
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        if (puStack_248 == (undefined1 *)0x0) {
          iVar16 = FUN_40004208((int)local_128);
          puStack_248 = (undefined1 *)(iVar16 + 1);
        }
        FUN_40004410((int)local_128,1,(int)puStack_248 - 1,(int *)&local_144);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)puStack_248 + 1,uVar11,(int *)ppuVar36);
        puStack_248 = (undefined1 *)FUN_400044f4(",",(char *)local_144);
        if (puStack_248 == (undefined1 *)0x0) {
          iVar16 = FUN_40004208((int)local_144);
          puStack_248 = (undefined1 *)(iVar16 + 1);
        }
        FUN_40004410((int)local_144,1,(uint)(puStack_248 + -1),(int *)&pbStack_770);
        local_13c = (undefined1 *)FUN_4000ab48(pbStack_770,0xffffffff,extraout_ECX_53);
        ppbVar28 = &pbStack_774;
        uVar11 = FUN_40004208((int)local_144);
        FUN_40004410((int)local_144,(int)(puStack_248 + 1),uVar11,(int *)ppbVar28);
        puStack_12c = (undefined1 *)FUN_4000ab48(pbStack_774,0xffffffff,extraout_ECX_54);
        if (-1 < (int)local_13c) {
          iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
          if (iVar16 <= (int)local_13c) {
            iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
            if (-1 < (int)local_13c - iVar16) {
              puStack_2ec = (undefined1 *)(((int)local_13c - iVar16) + 1);
              puStack_248 = (undefined1 *)0x0;
              do {
                (**(code **)(*DAT_400e7224 + 0x34))(DAT_400e7224,0);
                puStack_248 = puStack_248 + 1;
                puStack_2ec = puStack_2ec + -1;
              } while (puStack_2ec != (undefined1 *)0x0);
            }
          }
          (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&iStack_778);
          if (iStack_778 == 0) {
            (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
          }
          else {
            (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,local_13c,&uStack_77c);
            (**(code **)(*local_118 + 0x2c))(local_118,uStack_77c);
            if (((int)puStack_12c < 1) ||
               (iVar16 = (**(code **)(*local_118 + 0x14))(), iVar16 <= (int)(puStack_12c + -1))) {
              (**(code **)(*local_118 + 0x34))(local_118,local_128);
            }
            else {
              (**(code **)(*local_118 + 0x54))(local_118,puStack_12c + -1,local_128);
            }
            (**(code **)(*local_118 + 0x1c))(local_118,&uStack_780);
            (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,uStack_780);
          }
          func_0x400b9524(local_13c,local_128,puStack_12c);
        }
      }
      else if (bVar1 == 0x57) {
        FUN_40004140((int *)&local_128,(char *)(param_5 + 3));
        puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        if (puStack_248 == (undefined1 *)0x0) {
          iVar16 = FUN_40004208((int)local_128);
          puStack_248 = (undefined1 *)(iVar16 + 1);
        }
        FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&pbStack_768);
        local_13c = (undefined1 *)FUN_4000ab48(pbStack_768,0xffffffff,extraout_ECX_52);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
        if (-1 < (int)local_13c) {
          puVar6 = (undefined1 *)(**(code **)(*DAT_400e7224 + 0x14))();
          uVar18 = puVar6 == local_13c;
          if ((int)puVar6 <= (int)local_13c) {
            iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
            iVar16 = (int)local_13c - iVar16;
            uVar18 = iVar16 == 0;
            if (-1 < iVar16) {
              puStack_2ec = (undefined1 *)(iVar16 + 1);
              puStack_248 = (undefined1 *)0x0;
              do {
                (**(code **)(*DAT_400e7224 + 0x34))(DAT_400e7224,0);
                puStack_248 = puStack_248 + 1;
                puStack_2ec = puStack_2ec + -1;
                uVar18 = puStack_2ec == (undefined1 *)0x0;
              } while (!(bool)uVar18);
            }
          }
          FUN_40004410((int)local_128,1,1,(int *)&puStack_76c);
          FUN_40004318(puStack_76c,(uint *)&DAT_400adc24);
          if ((bool)uVar18) {
            ppuVar36 = &local_128;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar36);
          }
          (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,local_13c,local_128);
          FUN_400b9414((int)local_13c,(int)local_128);
        }
      }
      break;
    case 0x38:
      FUN_40004140((int *)&local_128,(char *)(param_5 + 2));
      local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
      if (local_13c == (undefined1 *)0x0) {
        iVar16 = FUN_40004208((int)local_128);
        local_13c = (undefined1 *)(iVar16 + 1);
      }
      ppuVar36 = &puStack_274;
      uVar11 = FUN_40004208((int)local_128);
      FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
      FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_128);
      local_13c = (undefined1 *)FUN_400044f4(",",(char *)puStack_274);
      if (local_13c == (undefined1 *)0x0) {
        iVar16 = FUN_40004208((int)puStack_274);
        local_13c = (undefined1 *)(iVar16 + 1);
      }
      ppuVar36 = &local_144;
      uVar11 = FUN_40004208((int)puStack_274);
      FUN_40004410((int)puStack_274,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
      uVar18 = local_13c + -1 == (undefined1 *)0x0;
      FUN_40004410((int)puStack_274,1,(uint)(local_13c + -1),(int *)&puStack_274);
      FUN_40004410((int)local_128,1,1,(int *)&puStack_8e4);
      FUN_40004318(puStack_8e4,(uint *)&DAT_400ad760);
      if ((bool)uVar18) {
        pFStack_2c8 = (FARPROC)0x0;
        ppuVar24 = &puStack_8ec;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar24);
        FUN_4000a8bc(puStack_8ec,&iStack_8e8);
        iVar16 = (**(code **)(*DAT_400e71e4 + 0x50))(DAT_400e71e4,iStack_8e8);
        if (iVar16 < 0) {
          ppuVar24 = &puStack_8f0;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar24);
          pCVar13 = FUN_400043cc(puStack_8f0);
          pHStack_2c4 = LoadLibraryA(pCVar13);
          ppuVar24 = &puStack_8f8;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar24);
          FUN_4000a8bc(puStack_8f8,&iStack_8f4);
          (**(code **)(*DAT_400e71e4 + 0x38))(DAT_400e71e4,iStack_8f4,pHStack_2c4);
        }
        else {
          ppuVar24 = &puStack_900;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar24);
          FUN_4000a8bc(puStack_900,&iStack_8fc);
          uVar10 = (**(code **)(*DAT_400e71e4 + 0x50))(DAT_400e71e4,iStack_8fc);
          pHStack_2c4 = (HMODULE)(**(code **)(*DAT_400e71e4 + 0x18))(DAT_400e71e4,uVar10);
        }
        if (pHStack_2c4 != (HMODULE)0x0) {
          pCVar13 = FUN_400043cc((undefined *)puStack_274);
          pFStack_2c8 = GetProcAddress(pHStack_2c4,pCVar13);
          if (pFStack_2c8 != (FARPROC)0x0) {
            iVar16 = *in_FS_OFFSET;
            *in_FS_OFFSET = (int)&stack0xffffffc8;
            pFVar14 = pFStack_2c8;
            while( true ) {
              FUN_400043cc((undefined *)local_144);
              local_13c = (undefined1 *)(*pFStack_2c8)(pFVar14,*param_4,_DAT_400e7210);
              iVar3 = _DAT_400e7210;
              if (local_13c != (undefined1 *)0xffffffff) break;
              _DAT_400e7210 = _DAT_400e7210 + 32000;
              FUN_400029c8((int *)param_4,iVar3 + 0x7d01);
              pFVar14 = (FARPROC)0xffffffff;
            }
            *in_FS_OFFSET = iVar16;
          }
        }
      }
      else {
        pFStack_2cc = (FARPROC)0x0;
        FUN_4000a8bc((undefined *)local_128,&iStack_904);
        iVar16 = (**(code **)(*DAT_400e71e4 + 0x50))(DAT_400e71e4,iStack_904);
        if (iVar16 < 0) {
          pCVar13 = FUN_400043cc((undefined *)local_128);
          pHStack_2c4 = LoadLibraryA(pCVar13);
          FUN_4000a8bc((undefined *)local_128,&iStack_908);
          (**(code **)(*DAT_400e71e4 + 0x38))(DAT_400e71e4,iStack_908,pHStack_2c4);
        }
        else {
          FUN_4000a8bc((undefined *)local_128,&iStack_90c);
          uVar10 = (**(code **)(*DAT_400e71e4 + 0x50))(DAT_400e71e4,iStack_90c);
          pHStack_2c4 = (HMODULE)(**(code **)(*DAT_400e71e4 + 0x18))(DAT_400e71e4,uVar10);
        }
        if (pHStack_2c4 != (HMODULE)0x0) {
          pCVar13 = FUN_400043cc((undefined *)puStack_274);
          pFStack_2cc = GetProcAddress(pHStack_2c4,pCVar13);
          if (pFStack_2cc != (FARPROC)0x0) {
            iVar16 = *in_FS_OFFSET;
            *in_FS_OFFSET = (int)&stack0xffffffc8;
            while( true ) {
              FUN_400043cc((undefined *)local_144);
              local_13c = (undefined1 *)(*pFStack_2cc)();
              iVar3 = _DAT_400e7210;
              if (local_13c != (undefined1 *)0xffffffff) break;
              _DAT_400e7210 = _DAT_400e7210 + 32000;
              FUN_400029c8((int *)param_4,iVar3 + 0x7d01);
            }
            *in_FS_OFFSET = iVar16;
          }
        }
      }
      break;
    case 0x39:
      ppuVar36 = &local_128;
      uVar11 = FUN_4000b140((char *)param_5);
      FUN_40004140(&local_910,(char *)param_5);
      FUN_40004410(local_910,4,uVar11,(int *)ppuVar36);
      CharUpperBuffA((LPSTR)(param_5 + 2),1);
      switch(param_5[2]) {
      case 0x20:
        FUN_4000a9b8((int)local_128,(int *)&local_278);
        break;
      case 0x21:
        FUN_4009f8cc((char *)local_128,&iStack_ae0,extraout_ECX_68,(int)&stack0xfffffffc);
        FUN_40004010((int *)&local_278,iStack_ae0);
        break;
      case 0x30:
        FUN_4000aa6c(param_6,(int *)&local_278);
        break;
      case 0x31:
        FUN_4000afc4((undefined *)local_128,(int *)&local_278);
        break;
      case 0x32:
        FUN_4000aea0((undefined *)local_128,(int *)&local_278);
        break;
      case 0x33:
        FUN_4000affc((undefined *)local_128,(int *)&local_278);
        break;
      case 0x34:
        func_0x4000af30(local_128,&local_278);
        break;
      case 0x35:
        FUN_40021570((undefined *)local_128,&local_914);
        uVar11 = FUN_4000482c((int)local_914);
        FUN_4000aa6c(uVar11,(int *)&local_278);
        break;
      case 0x36:
        FUN_40004410((int)local_128,1,1,(int *)&local_144);
        local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        if (local_13c == (undefined1 *)0x0) {
          ppuVar36 = &local_278;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar36);
        }
        else {
          ppuVar24 = &puStack_918;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar24);
          FUN_40021570(puStack_918,&pOStack_2b0);
          uVar18 = local_13c + -2 == (undefined1 *)0x0;
          FUN_40004410((int)local_128,2,(uint)(local_13c + -2),(int *)&local_128);
          FUN_40004410((int)local_128,1,1,(int *)&puStack_91c);
          FUN_40004318(puStack_91c,(uint *)&DAT_400ad760);
          if ((bool)uVar18) {
            local_13c = (undefined1 *)FUN_400044f4(".",(char *)local_128);
            if (local_13c == (undefined1 *)0x0) {
              iVar16 = FUN_40004208((int)local_128);
              local_13c = (undefined1 *)(iVar16 + 1);
            }
            FUN_40004410((int)local_128,2,(uint)(local_13c + -2),(int *)&pbStack_920);
            uVar18 = 1;
            puStack_130 = (undefined1 *)FUN_4000ab48(pbStack_920,0,extraout_ECX_69);
            ppuVar36 = &local_128;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)local_13c,uVar11,(int *)ppuVar36);
          }
          else {
            uVar18 = 1;
            puStack_130 = (undefined1 *)0x0;
          }
          FUN_40004410((int)local_128,1,1,(int *)&puStack_924);
          FUN_40004318(puStack_924,(uint *)&DAT_400ad754);
          if ((bool)uVar18) {
            ppbVar28 = &pbStack_928;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,2,uVar11,(int *)ppbVar28);
            uVar18 = 0;
            UStack_134 = FUN_4000ab48(pbStack_928,0xffffffff,extraout_ECX_70);
          }
          else {
            UStack_134 = 0xffffffff;
          }
          FUN_40004318(local_144,(uint *)&DAT_400ad7b0);
          if ((bool)uVar18) {
            if ((int)UStack_134 < 0) {
              ppOVar31 = &pOStack_2b0;
              uVar11 = FUN_4000482c((int)pOStack_2b0);
              FUN_400049e0((int)pOStack_2b0,(int)(puStack_130 + 1),uVar11,(BSTR)ppOVar31);
            }
            else {
              FUN_400049e0((int)pOStack_2b0,(int)(puStack_130 + 1),UStack_134,(BSTR)&pOStack_2b0);
            }
          }
          else {
            uVar11 = FUN_4000482c((int)pOStack_2b0);
            if ((int)uVar11 < (int)puStack_130) {
              puStack_130 = (undefined1 *)FUN_4000482c((int)pOStack_2b0);
            }
            if ((-1 < (int)UStack_134) &&
               (uVar11 = FUN_4000482c((int)pOStack_2b0),
               (int)uVar11 < (int)(puStack_130 + UStack_134))) {
              uVar11 = FUN_4000482c((int)pOStack_2b0);
              UStack_134 = uVar11 - (int)puStack_130;
            }
            if ((int)UStack_134 < 0) {
              ppOVar31 = &pOStack_2b0;
              uVar11 = FUN_4000482c((int)pOStack_2b0);
              FUN_400049e0((int)pOStack_2b0,1,uVar11 - (int)puStack_130,(BSTR)ppOVar31);
            }
            else {
              ppOVar31 = &pOStack_2b0;
              uVar11 = FUN_4000482c((int)pOStack_2b0);
              FUN_400049e0((int)pOStack_2b0,((uVar11 - (int)puStack_130) - UStack_134) + 1,
                           UStack_134,(BSTR)ppOVar31);
            }
          }
          FUN_40021554((int *)pOStack_2b0,(int *)&local_278);
        }
        break;
      case 0x37:
        FUN_40026f28((undefined *)local_128,(int *)&local_278);
        break;
      case 0x38:
        FUN_40021570((undefined *)local_128,&pWStack_2a8);
        ppOVar31 = &pOStack_2b0;
        uVar11 = FUN_4000482c((int)pWStack_2a8);
        FUN_400049e0((int)pWStack_2a8,3,uVar11,(BSTR)ppOVar31);
        local_13c = (undefined1 *)FUN_4000482c((int)pOStack_2b0);
        if (0 < (int)local_13c) {
          puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = local_13c;
          do {
            if (pOStack_2b0[(int)(puStack_114 + -1)] == *pWStack_2a8) {
              pOStack_2b0[(int)(puStack_114 + -1)] = pWStack_2a8[1];
            }
            puStack_114 = puStack_114 + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        FUN_40021554((int *)pOStack_2b0,(int *)&local_278);
        break;
      case 0x39:
        FUN_400232a8((int)local_128,&iStack_92c);
        (**(code **)(*local_118 + 0x2c))(local_118,iStack_92c);
        puVar6 = (undefined1 *)(**(code **)(*local_118 + 0x14))();
        if (-1 < (int)(puVar6 + -1)) {
          local_13c = (undefined1 *)0x0;
          puStack_2ec = puVar6;
          do {
            (**(code **)(*local_118 + 0xc))(local_118,local_13c,&pcStack_930);
            puStack_114 = (undefined1 *)FUN_400044f4("#",pcStack_930);
            if (puStack_114 != (undefined1 *)0x0) {
              ppuVar36 = &local_128;
              (**(code **)(*local_118 + 0xc))(local_118,local_13c,&iStack_934);
              uVar11 = FUN_40004208(iStack_934);
              (**(code **)(*local_118 + 0xc))(local_118,local_13c,&iStack_938);
              FUN_40004410(iStack_938,(int)(puStack_114 + 1),uVar11,(int *)ppuVar36);
              ppbVar28 = &pbStack_93c;
              (**(code **)(*local_118 + 0xc))(local_118,local_13c,&iStack_940);
              FUN_40004410(iStack_940,1,(uint)(puStack_114 + -1),(int *)ppbVar28);
              puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_93c,0,extraout_ECX_71);
              if (0 < (int)puStack_114) {
                iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
                if (iVar16 <= (int)puStack_114) {
                  iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
                  if (-1 < (int)puStack_114 - iVar16) {
                    iStack_2f0 = ((int)puStack_114 - iVar16) + 1;
                    puStack_248 = (undefined1 *)0x0;
                    do {
                      (**(code **)(*DAT_400e7224 + 0x34))(DAT_400e7224,0);
                      puStack_248 = puStack_248 + 1;
                      iStack_2f0 = iStack_2f0 + -1;
                    } while (iStack_2f0 != 0);
                  }
                }
                (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,puStack_114,&iStack_944);
                FUN_40004210(&iStack_944,local_128);
                (**(code **)(*DAT_400e7224 + 0x20))(DAT_400e7224,puStack_114,iStack_944);
              }
            }
            local_13c = local_13c + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        FUN_400b9308();
        FUN_40003f78((int *)&local_278);
        break;
      case 0x3f:
        uVar10 = FUN_4009f614((char *)local_128,extraout_EDX_00,extraout_ECX_68,&stack0xfffffffc);
        FUN_4000aa6c(uVar10,(int *)&local_278);
        break;
      case 0x41:
        iVar16 = *in_FS_OFFSET;
        *in_FS_OFFSET = (int)&stack0xffffffc8;
        iVar3 = FUN_400044f4(":",(char *)local_128);
        if (((iVar3 < 1) && (iVar3 = FUN_400044f4("\\\\",(char *)local_128), iVar3 != 1)) &&
           (iVar3 = FUN_400044f4(".\\",(char *)local_128), iVar3 != 1)) {
          ppuVar38 = &puStack_948;
          iVar3 = FUN_400044f4("\\",(char *)local_128);
          iVar3 = iVar3 + 1;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,iVar3,uVar11,(int *)ppuVar38);
          FUN_40004254((int *)&local_128,(undefined4 *)&DAT_400add3c,puStack_948);
        }
        iVar3 = FUN_400044f4(".",(char *)local_128);
        if (iVar3 == 1) {
          FUN_40004140(&iStack_94c,DAT_400e71f4);
          FUN_40004140((int *)&puStack_954,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_954,&iStack_950);
          piVar21 = &iStack_958;
          uStack_50 = (double)CONCAT44(0x400a938d,(undefined *)uStack_50);
          iVar3 = FUN_40004208((int)local_128);
          uStack_50 = (double)CONCAT44(0x400a93a0,(undefined *)uStack_50);
          FUN_40004410((int)local_128,2,iVar3 - 1,piVar21);
          uStack_50 = (double)CONCAT44(&LAB_400a93b6,(undefined *)uStack_50);
          FUN_400042c8((int *)&local_128,4);
        }
        uVar10 = FUN_4000ad04((undefined *)local_128);
        if ((char)uVar10 == '\0') {
          FUN_400237a8((undefined *)local_128,&iStack_95c);
          FUN_40004010((int *)&local_128,iStack_95c);
        }
        uVar10 = FUN_4000ad04((undefined *)local_128);
        if ((char)uVar10 == '\0') {
          FUN_40004010((int *)&local_278,0x400ad7b0);
        }
        else {
          puStack_248 = (undefined1 *)FUN_4000ab94((undefined *)local_128,0x40);
          puStack_114 = (undefined1 *)GetFileSize(puStack_248,(LPDWORD)&local_13c);
          FUN_40026c7c((int)local_13c,(int)puStack_114,extraout_ECX_72);
          func_0x4000aa9c(&local_278);
          FUN_4000ac94(puStack_248);
        }
        *in_FS_OFFSET = iVar16;
        break;
      case 0x42:
        iVar16 = FUN_40004208((int)local_128);
        if (2 < iVar16) {
          FUN_40004410((int)local_128,1,1,(int *)&local_278);
          FUN_40004410((int)local_128,2,1,(int *)&local_140);
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,3,uVar11,(int *)ppuVar36);
          while( true ) {
            FUN_40004120((int *)&pcStack_968,CONCAT31((int3)((uint)local_278 >> 8),(byte)*local_278)
                        );
            iVar16 = FUN_400044f4(pcStack_968,(char *)local_128);
            if (iVar16 < 1) break;
            iVar16 = FUN_400044f4((char *)local_278,(char *)local_128);
            iVar3 = FUN_400043d8((int *)&local_128);
            *(char *)(iVar3 + -1 + iVar16) = (char)*local_140;
          }
        }
        FUN_40004010((int *)&local_278,(int)local_128);
        break;
      case 0x43:
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_96c);
        puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_96c,0,extraout_ECX_73);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_144);
        if (local_144 == (uint *)0x0) {
          FUN_40004140((int *)&puStack_970,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_970,(int *)&local_144);
        }
        FUN_40089484((int *)&local_144,DAT_400e7218);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        switch(puStack_114) {
        case (undefined1 *)0x0:
          FUN_40004140((int *)&puStack_974,DAT_400e71f0);
          FUN_40004254((int *)&local_128,puStack_974,local_128);
          break;
        case (undefined1 *)0x1:
          FUN_40004140((int *)&puStack_978,DAT_400e71f4);
          FUN_40004254((int *)&local_128,puStack_978,local_128);
          break;
        case (undefined1 *)0x2:
          if (8 < *(int *)(DAT_400e7218 + 0xc)) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,0);
            FUN_40004140((int *)&puStack_97c,pcVar12);
            FUN_40004254((int *)&local_128,puStack_97c,local_128);
          }
          break;
        case (undefined1 *)0x3:
          if (8 < *(int *)(DAT_400e7218 + 0xc)) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,1);
            FUN_40004140((int *)&puStack_980,pcVar12);
            FUN_40004254((int *)&local_128,puStack_980,local_128);
          }
          break;
        case (undefined1 *)0xa:
          if (8 < *(int *)(DAT_400e7218 + 0xc)) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,9);
            FUN_40004140((int *)&puStack_984,pcVar12);
            FUN_40004254((int *)&local_128,puStack_984,local_128);
          }
        }
        uVar18 = DAT_400e71cc == (int *)0x0;
        if ((bool)uVar18) {
LAB_400a995e:
          FUN_4002627c(local_144,(undefined *)local_128,DAT_400e71f8,local_118);
        }
        else {
          (**(code **)*DAT_400e71cc)(DAT_400e71cc,&DAT_400adb78,"DepositPriority");
          FUN_40004318(puStack_988,(uint *)&DAT_400adb24);
          if (!(bool)uVar18) goto LAB_400a995e;
          FUN_400267fc(local_144,(undefined *)local_128,DAT_400e71f8,local_118,(char)local_118);
        }
        if (param_6 == (undefined1 *)0x0) {
          (**(code **)(*local_118 + 0x1c))(local_118,&puStack_98c);
          FUN_40023740(puStack_98c,(int *)&local_278);
        }
        else {
          iVar16 = (**(code **)(*local_118 + 0x14))();
          if (iVar16 < (int)param_6) {
            FUN_40003f78((int *)&local_278);
          }
          else {
            (**(code **)(*local_118 + 0xc))(local_118,param_6 + -1,&puStack_990);
            FUN_40023740(puStack_990,(int *)&local_278);
          }
        }
        break;
      case 0x44:
        FUN_40003f78((int *)&local_278);
        local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_128);
        if (0 < (int)local_13c) {
          ppuVar36 = &local_144;
          uVar11 = FUN_40004208((int)local_128);
          uVar18 = local_13c + 1 == (undefined1 *)0x0;
          FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
          FUN_40004410((int)local_128,1,1,(int *)&puStack_a74);
          FUN_40004318(puStack_a74,(uint *)&DAT_400ad760);
          if ((bool)uVar18) {
            local_13c = param_6;
          }
          else {
            FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_a78);
            local_13c = (undefined1 *)FUN_4000ab48(pbStack_a78,1,extraout_ECX_79);
          }
          if (DAT_400e71cc == (int *)0x0) {
            iStack_124 = 0x3b9;
          }
          else {
            iStack_124 = (**(code **)(*DAT_400e71cc + 8))
                                   (DAT_400e71cc,&DAT_400adb78,"TAGINTERNALRESOURCE");
          }
          FUN_4000affc((undefined *)local_144,&iStack_a7c);
          if (iStack_a7c == 0) {
            pcVar12 = "A";
            iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)local_13c);
            pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,pcVar12);
            FUN_40004140(&iStack_a80,pcVar12);
            FUN_400042c8((int *)&local_144,3);
          }
          puVar5 = (uint *)&DAT_400ade74;
          iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)local_13c);
          pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,(char *)puVar5);
          FUN_40004140(&iStack_a84,pcVar12);
          FUN_400232a8(iStack_a84,(int *)&local_128);
          iVar16 = *in_FS_OFFSET;
          *in_FS_OFFSET = (int)&stack0xffffffc8;
          FUN_4000aea0((undefined *)local_144,(int *)&puStack_a88);
          FUN_4008663c(puStack_a88);
          uVar22 = 0;
          uVar23 = 0;
          pCVar13 = FUN_400043cc((undefined *)local_144);
          local_13c = (undefined1 *)_lcreat(pCVar13,CONCAT22(uVar23,uVar22));
          uVar10 = FUN_40004208((int)local_128);
          uVar22 = (undefined2)uVar10;
          uVar23 = (undefined2)((uint)uVar10 >> 0x10);
          lpBuffer = FUN_400043cc((undefined *)local_128);
          _lwrite((HFILE)local_13c,lpBuffer,CONCAT22(uVar23,uVar22));
          _lclose((HFILE)local_13c);
          *in_FS_OFFSET = iVar16;
        }
        break;
      case 0x45:
        iVar16 = *in_FS_OFFSET;
        *in_FS_OFFSET = (int)&stack0xffffffc8;
        iVar3 = FUN_4000ab48((byte *)local_128,0,extraout_ECX_68);
        if (iVar3 < 1) {
          FUN_40004010((int *)&local_278,0x400ad7b0);
        }
        else {
          FUN_40028234((undefined *)local_128);
          if ((float10)_DAT_400add40 <= in_ST0) {
            FUN_40028234((undefined *)local_128);
            if ((float10)_DAT_400add50 <= in_ST1) {
              FUN_40028234((undefined *)local_128);
              uVar10 = FUN_40002cf0();
              uStack_3f8 = (double)CONCAT44(extraout_EDX_01,uVar10);
              FUN_4000ba34((int *)&puStack_964);
              FUN_40004254((int *)&local_278,puStack_964,(undefined4 *)&DAT_400add68);
            }
            else {
              FUN_40028234((undefined *)local_128);
              FUN_4000ba34((int *)&puStack_960);
              FUN_40004254((int *)&local_278,puStack_960,(undefined4 *)&DAT_400add5c);
            }
          }
          else {
            FUN_40004254((int *)&local_278,local_128,(undefined4 *)&DAT_400add4c);
          }
        }
        *in_FS_OFFSET = iVar16;
        break;
      case 0x46:
        uVar10 = FUN_4000ab48((byte *)local_128,0x3f,extraout_ECX_68);
        FUN_40004120((int *)&puStack_a8c,uVar10);
        FUN_40023740(puStack_a8c,(int *)&local_278);
        break;
      case 0x47:
        FUN_4008ea9c((undefined *)local_128,&iStack_a90,extraout_ECX_68,(int)&stack0xfffffffc);
        FUN_40004010((int *)&local_278,iStack_a90);
        break;
      case 0x48:
        FUN_40003f78((int *)&local_278);
        iVar16 = FUN_40004208((int)local_128);
        if (1 < iVar16) {
          FUN_40004410((int)local_128,1,1,(int *)&local_144);
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar36);
          local_13c = (undefined1 *)FUN_400044f4((char *)local_144,(char *)local_128);
          if ((0 < (int)local_13c) &&
             (iVar16 = FUN_40004208((int)local_128), (int)local_13c < iVar16)) {
            ppuVar38 = &puStack_a94;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar38);
            FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&puStack_a98);
            FUN_40004254((int *)&local_278,puStack_a98,puStack_a94);
          }
        }
        break;
      case 0x49:
        if (local_128 != (uint *)0x0) {
          FUN_40004120((int *)&local_144,CONCAT31((int3)((uint)local_128 >> 8),(char)*local_128));
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar36);
          local_13c = (undefined1 *)FUN_400044f4((char *)local_144,(char *)local_128);
          if (0 < (int)local_13c) {
            FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_278);
            ppuVar36 = &local_128;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
            if ((local_278 != (uint *)0x0) && (local_128 != (uint *)0x0)) {
              FUN_40004120((int *)&local_144,CONCAT31((int3)((uint)local_128 >> 8),(char)*local_128)
                          );
              ppuVar36 = &local_128;
              uVar11 = FUN_40004208((int)local_128);
              FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar36);
              local_13c = (undefined1 *)FUN_400044f4((char *)local_144,(char *)local_128);
              if (0 < (int)local_13c) {
                FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_140);
                ppuVar36 = &local_128;
                uVar11 = FUN_40004208((int)local_128);
                FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
                puStack_114 = (undefined1 *)0x0;
                puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
                while( true ) {
                  FUN_40026f28((undefined *)local_128,&iStack_a9c);
                  iVar16 = iStack_a9c;
                  FUN_40026f28((undefined *)local_278,(int *)&pcStack_aa0);
                  local_13c = (undefined1 *)FUN_40088058(pcStack_aa0,iVar16,(int)puStack_248);
                  if (local_13c == (undefined1 *)0x0) break;
                  FUN_40004410((int)local_128,1,(uint)(local_13c + -1),&iStack_aa4);
                  ppuVar36 = &puStack_aa8;
                  uVar10 = FUN_40004208((int)local_128);
                  uVar22 = (undefined2)uVar10;
                  uVar23 = (undefined2)((uint)uVar10 >> 0x10);
                  iVar16 = FUN_40004208((int)local_278);
                  FUN_40004410((int)local_128,(int)(local_13c + iVar16),CONCAT22(uVar23,uVar22),
                               (int *)ppuVar36);
                  puVar5 = puStack_aa8;
                  FUN_400042c8((int *)&local_128,3);
                  puStack_114 = puStack_114 + 1;
                  if (100 < (int)puStack_114) break;
                  iVar16 = FUN_40004208((int)local_140);
                  puStack_248 = local_13c + iVar16;
                }
              }
            }
          }
        }
        FUN_40004010((int *)&local_278,(int)local_128);
        break;
      case 0x4a:
        FUN_4009cc3c((undefined *)local_128,&iStack_aac);
        FUN_40004010((int *)&local_278,iStack_aac);
        break;
      case 0x4b:
        FUN_4009ce50((undefined *)local_128);
        FUN_40003f78((int *)&local_278);
        break;
      case 0x4c:
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_994);
        puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_994,0,extraout_ECX_74);
        bVar20 = (int)puStack_114 < 0;
        if (bVar20) {
          puStack_114 = (undefined1 *)-(int)puStack_114;
        }
        puStack_25c = (undefined1 *)(uint)bVar20;
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_144);
        if (local_144 == (uint *)0x0) {
          FUN_40004140((int *)&puStack_998,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_998,(int *)&local_144);
        }
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        switch(puStack_114) {
        case (undefined1 *)0x0:
          FUN_40004140((int *)&puStack_99c,DAT_400e71f0);
          FUN_40004254((int *)&local_128,puStack_99c,local_128);
          break;
        case (undefined1 *)0x1:
          FUN_40004140((int *)&puStack_9a0,DAT_400e71f4);
          FUN_40004254((int *)&local_128,puStack_9a0,local_128);
          break;
        case (undefined1 *)0x2:
        case (undefined1 *)0x3:
        case (undefined1 *)0xa:
          FUN_40089484((int *)&local_144,DAT_400e7218);
          if (puStack_114 == (undefined1 *)((int)&iRam00000000 + 2)) {
            if (8 < *(int *)(DAT_400e7218 + 0xc)) {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7218,0);
              FUN_40004140((int *)&puStack_9a8,pcVar12);
              FUN_40004254((int *)&local_128,puStack_9a8,local_128);
            }
          }
          else if (puStack_114 == (undefined1 *)((int)&iRam00000000 + 3)) {
            if (8 < *(int *)(DAT_400e7218 + 0xc)) {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7218,1);
              FUN_40004140((int *)&puStack_9ac,pcVar12);
              FUN_40004254((int *)&local_128,puStack_9ac,local_128);
            }
          }
          else if ((puStack_114 == (undefined1 *)0xa) && (8 < *(int *)(DAT_400e7218 + 0xc))) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,9);
            FUN_40004140((int *)&puStack_9b0,pcVar12);
            FUN_40004254((int *)&local_128,puStack_9b0,local_128);
          }
          break;
        case (undefined1 *)0xc:
          FUN_40089484((int *)&local_144,DAT_400e7218);
          if (8 < *(int *)(DAT_400e7218 + 0xc)) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,10);
            FUN_40004140((int *)&puStack_9a4,pcVar12);
            FUN_40004254((int *)&local_128,puStack_9a4,local_128);
          }
        }
        uVar18 = puStack_114 == (undefined1 *)0xb;
        if ((bool)uVar18) {
          FUN_40004410((int)local_128,1,2,(int *)&puStack_9b4);
          FUN_40004318(puStack_9b4,(uint *)&DAT_400add30);
          if (!(bool)uVar18) {
            FUN_40004410((int)local_128,1,2,(int *)&puStack_9b8);
            FUN_40004318(puStack_9b8,(uint *)&DAT_400add74);
            if (!(bool)uVar18) {
              FUN_40004410((int)local_128,2,1,(int *)&local_9bc);
              FUN_40004318(local_9bc,(uint *)&DAT_400add24);
              if (!(bool)uVar18) {
                uVar11 = FUN_4009d360((byte *)local_128);
                FUN_4000aa6c(uVar11 & 0x7f,(int *)&local_278);
                break;
              }
            }
          }
        }
        if (puStack_25c == (undefined1 *)0x0) {
          uVar10 = FUN_4000ad04((undefined *)local_128);
          if ((char)uVar10 == '\0') {
            FUN_400237a8((undefined *)local_128,(int *)&pCStack_9c4);
            FUN_400047a8((BSTR)&local_9c0,pCStack_9c4);
            uVar11 = FUN_4002061c(local_9c0);
            FUN_4000aa6c(uVar11 & 0x7f,(int *)&local_278);
          }
          else {
            uVar11 = FUN_4000ad04((undefined *)local_128);
            FUN_4000aa6c(uVar11 & 0x7f,(int *)&local_278);
          }
        }
        else {
          bStack_279 = true;
          FUN_4009dcd0(2,&bStack_279,&iStack_9c8,&stack0xfffffffc);
          FUN_40004010((int *)&local_278,iStack_9c8);
          if (bStack_279 == false) {
            FUN_400237a8((undefined *)local_128,(int *)&puStack_9cc);
            uVar10 = FUN_4000ad04(puStack_9cc);
            if ((char)uVar10 != '\0') {
              FUN_400237a8((undefined *)local_128,&local_9d0);
              FUN_40004010((int *)&local_128,local_9d0);
            }
            uVar10 = FUN_4000ad04((undefined *)local_128);
            if ((char)uVar10 != '\0') {
              FUN_400047a8((BSTR)&local_9d4,(LPCSTR)local_128);
              FUN_400784f0(local_9d4,(int *)0x0,(int *)&local_278);
            }
          }
        }
        break;
      case 0x4e:
        FUN_4009d05c((char *)local_128,0,&iStack_ab0,(int)&stack0xfffffffc);
        FUN_40004010((int *)&local_278,iStack_ab0);
        break;
      case 0x50:
        FUN_4009d05c((char *)local_128,1,&iStack_ab4,(int)&stack0xfffffffc);
        FUN_40004010((int *)&local_278,iStack_ab4);
        break;
      case 0x52:
        if (local_128 == (uint *)0x0) {
          FUN_40003f78((int *)&local_278);
        }
        else {
          uVar10 = FUN_40087188(local_128);
          FUN_4000aa6c(uVar10,(int *)&local_278);
        }
        break;
      case 0x53:
        ppcVar33 = &pcStack_ab8;
        iVar16 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,2,iVar16 - 1,(int *)ppcVar33);
        FUN_40004410((int)local_128,1,1,(int *)&pcStack_abc);
        local_13c = (undefined1 *)FUN_400044f4(pcStack_abc,pcStack_ab8);
        if (0 < (int)local_13c) {
          FUN_40004410((int)local_128,2,(uint)(local_13c + -1),(int *)&puStack_ac0);
          FUN_40026f28(puStack_ac0,(int *)&local_144);
          ppuVar24 = &local_ac8;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(local_13c + 2),uVar11,(int *)ppuVar24);
          FUN_40026f28(local_ac8,&iStack_ac4);
          FUN_40004010((int *)&local_128,iStack_ac4);
          FUN_40021570((undefined *)local_128,&pOStack_acc);
          FUN_40021570((undefined *)local_144,&local_ad0);
          local_13c = (undefined1 *)FUN_40004a2c(local_ad0,pOStack_acc);
        }
        FUN_4000aa6c(local_13c,(int *)&local_278);
        break;
      case 0x54:
        local_13c = (undefined1 *)FUN_400044f4("/",(char *)local_128);
        if (local_13c != (undefined1 *)0x0) {
          uVar11 = 0;
          FUN_40004410((int)local_128,1,(uint)(local_13c + -1),&iStack_ad4);
          uStack_294 = FUN_4000ab60(iStack_ad4,extraout_EDX_02,extraout_ECX_80,uVar11);
          uVar7 = 0;
          piVar21 = &iStack_ad8;
          iStack_290 = extraout_EDX_03;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,piVar21);
          uStack_29c = FUN_4000ab60(iStack_ad8,extraout_EDX_04,extraout_ECX_81,uVar7);
          iStack_298 = extraout_EDX_05;
          FUN_40003f78((int *)&local_278);
          uVar10 = extraout_ECX_82;
          do {
            if (iStack_290 == iStack_298) {
              if (uStack_29c < uStack_294) goto LAB_400ab751;
            }
            else if (iStack_298 < iStack_290) goto LAB_400ab751;
            if (local_278 != (uint *)0x0) {
              FUN_40004210((int *)&local_278,(undefined4 *)&DAT_400adc24);
              uVar10 = extraout_ECX_83;
            }
            FUN_40027a40((uint)(local_13c + -1),(int *)&puStack_adc,uVar10,uStack_294,iStack_290);
            FUN_40004210((int *)&local_278,puStack_adc);
            bVar20 = 0xfffffffe < uStack_294;
            uStack_294 = uStack_294 + 1;
            iStack_290 = iStack_290 + (uint)bVar20;
            uVar10 = extraout_ECX_84;
          } while( true );
        }
        FUN_40004010((int *)&local_278,(int)local_128);
        break;
      case 0x55:
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_9d8);
        puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_9d8,0,extraout_ECX_75);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_144);
        if (local_144 == (uint *)0x0) {
          FUN_40004140((int *)&puStack_9dc,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_9dc,(int *)&local_144);
        }
        uStack_24c = 1;
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        if ((int)local_13c < 1) {
          iStack_258 = 200;
        }
        else {
          FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_9e0);
          iStack_258 = FUN_4000ab48(pbStack_9e0,200,extraout_ECX_76);
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
          local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
          if ((int)local_13c < 1) {
            uStack_24c = 1;
          }
          else {
            FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_9e4);
            uStack_24c = FUN_4000ab48(pbStack_9e4,1,extraout_ECX_77);
            ppuVar36 = &local_128;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
          }
        }
        FUN_40004010(local_254,(int)local_128);
        FUN_400237a8((undefined *)local_128,&iStack_9e8);
        FUN_40004010((int *)&local_128,iStack_9e8);
        bStack_279 = (int)puStack_114 < 0;
        if (bStack_279) {
          puStack_114 = (undefined1 *)-(int)puStack_114;
        }
        switch(puStack_114) {
        case (undefined1 *)0x0:
          FUN_40004140((int *)&puStack_9ec,DAT_400e71f0);
          FUN_40004254((int *)&local_128,puStack_9ec,local_128);
          break;
        case (undefined1 *)0x1:
          FUN_40004140((int *)&puStack_9f0,DAT_400e71f4);
          FUN_40004254((int *)&local_128,puStack_9f0,local_128);
          break;
        case (undefined1 *)0x2:
        case (undefined1 *)0x3:
        case (undefined1 *)0xa:
          FUN_40089484((int *)&local_144,DAT_400e7218);
          if (puStack_114 == (undefined1 *)((int)&iRam00000000 + 2)) {
            if (8 < *(int *)(DAT_400e7218 + 0xc)) {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7218,0);
              FUN_40004140((int *)&puStack_9f8,pcVar12);
              FUN_40004254((int *)&local_128,puStack_9f8,local_128);
            }
          }
          else if (puStack_114 == (undefined1 *)((int)&iRam00000000 + 3)) {
            if (8 < *(int *)(DAT_400e7218 + 0xc)) {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7218,1);
              FUN_40004140((int *)&puStack_9fc,pcVar12);
              FUN_40004254((int *)&local_128,puStack_9fc,local_128);
            }
          }
          else if ((puStack_114 == (undefined1 *)0xa) && (8 < *(int *)(DAT_400e7218 + 0xc))) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,9);
            FUN_40004140((int *)&puStack_a00,pcVar12);
            FUN_40004254((int *)&local_128,puStack_a00,local_128);
          }
          break;
        case (undefined1 *)0xc:
          FUN_40089484((int *)&local_144,DAT_400e7218);
          if (8 < *(int *)(DAT_400e7218 + 0xc)) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,10);
            FUN_40004140((int *)&puStack_9f4,pcVar12);
            FUN_40004254((int *)&local_128,puStack_9f4,local_128);
          }
        }
        puVar6 = (undefined1 *)FUN_40004208((int)local_128);
        if (0 < (int)puVar6) {
          local_13c = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = puVar6;
          do {
            if (local_13c[(int)local_128 + -1] == '/') {
              iVar16 = FUN_400043d8((int *)&local_128);
              local_13c[iVar16 + -1] = 0x5c;
            }
            local_13c = local_13c + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        if (bStack_279 != false) {
          FUN_4009dcd0(1,&bStack_279,&local_a04,&stack0xfffffffc);
          FUN_40004010((int *)&local_278,local_a04);
        }
        if (bStack_279 == false) {
          uVar10 = FUN_4000ad04((undefined *)local_128);
          if ((char)uVar10 == '\0') {
            FUN_40003f78((int *)&local_278);
          }
          else {
            ppuVar36 = &local_278;
            iVar16 = iStack_258;
            FUN_400047a8((BSTR)&local_a08,(LPCSTR)local_128);
            FUN_40077d1c(local_a08,(int *)0x0,uStack_24c,(int *)ppuVar36,iVar16);
          }
        }
        break;
      case 0x56:
        FUN_40004010((int *)&local_278,0x400adea4);
        break;
      case 0x58:
        if (local_128 == (uint *)0x0) {
          FUN_40003f78((int *)&local_278);
        }
        else {
          iVar16 = FUN_4000ab48((byte *)local_128,0,extraout_ECX_68);
          FUN_400870d8(iVar16,(int *)&local_278);
        }
        break;
      case 0x59:
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&pbStack_a0c);
        puStack_114 = (undefined1 *)FUN_4000ab48(pbStack_a0c,0,extraout_ECX_78);
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&local_144);
        if (local_144 == (uint *)0x0) {
          FUN_40004140((int *)&puStack_a10,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_a10,(int *)&local_144);
        }
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        FUN_400237a8((undefined *)local_128,&iStack_a14);
        FUN_40004010((int *)&local_128,iStack_a14);
        switch(puStack_114) {
        case (undefined1 *)0x0:
          FUN_40004140((int *)&puStack_a18,DAT_400e71f0);
          FUN_40004254((int *)&local_128,puStack_a18,local_128);
          break;
        case (undefined1 *)0x1:
          FUN_40004140((int *)&puStack_a1c,DAT_400e71f4);
          FUN_40004254((int *)&local_128,puStack_a1c,local_128);
          break;
        case (undefined1 *)0x2:
        case (undefined1 *)0x3:
        case (undefined1 *)0xa:
          FUN_40089484((int *)&local_144,DAT_400e7218);
          if (puStack_114 == (undefined1 *)((int)&iRam00000000 + 2)) {
            if (8 < *(int *)(DAT_400e7218 + 0xc)) {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7218,0);
              FUN_40004140((int *)&puStack_a24,pcVar12);
              FUN_40004254((int *)&local_128,puStack_a24,local_128);
            }
          }
          else if (puStack_114 == (undefined1 *)((int)&iRam00000000 + 3)) {
            if (8 < *(int *)(DAT_400e7218 + 0xc)) {
              pcVar12 = (char *)FUN_4002934c(DAT_400e7218,1);
              FUN_40004140((int *)&puStack_a28,pcVar12);
              FUN_40004254((int *)&local_128,puStack_a28,local_128);
            }
          }
          else if ((puStack_114 == (undefined1 *)0xa) && (8 < *(int *)(DAT_400e7218 + 0xc))) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,9);
            FUN_40004140((int *)&puStack_a2c,pcVar12);
            FUN_40004254((int *)&local_128,puStack_a2c,local_128);
          }
          break;
        case (undefined1 *)0xc:
          FUN_40089484((int *)&local_144,DAT_400e7218);
          if (8 < *(int *)(DAT_400e7218 + 0xc)) {
            pcVar12 = (char *)FUN_4002934c(DAT_400e7218,10);
            FUN_40004140((int *)&puStack_a20,pcVar12);
            FUN_40004254((int *)&local_128,puStack_a20,local_128);
          }
        }
        puVar6 = (undefined1 *)FUN_40004208((int)local_128);
        if (0 < (int)puVar6) {
          local_13c = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = puVar6;
          do {
            if (local_13c[(int)local_128 + -1] == '/') {
              iVar16 = FUN_400043d8((int *)&local_128);
              local_13c[iVar16 + -1] = 0x5c;
            }
            local_13c = local_13c + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        uVar10 = FUN_4000ad04((undefined *)local_128);
        cVar2 = (char)uVar10;
        if (cVar2 == '\0') {
          FUN_40004010((int *)&local_278,0x400ade50);
        }
        else {
          if (DAT_400e71cc != (int *)0x0) {
            iVar16 = (**(code **)(*DAT_400e71cc + 8))
                               (DAT_400e71cc,"FullText","CheckPDF_with_Quickdll");
            cVar2 = '\x01';
            if (iVar16 != 1) {
              if (DAT_400e71cc == (int *)0x0) {
                local_13c = (undefined1 *)((int)&iRam00000000 + 1);
              }
              else {
                local_13c = (undefined1 *)
                            (**(code **)(*DAT_400e71cc + 8))
                                      (DAT_400e71cc,"FullText","PDFPageNumber");
              }
              if (DAT_400e71cc == (int *)0x0) {
                puStack_114 = &DAT_00000005;
              }
              else {
                puStack_114 = (undefined1 *)
                              (**(code **)(*DAT_400e71cc + 8))
                                        (DAT_400e71cc,"FullText","PDFExtractTime");
              }
              GetCurrentProcessId();
              func_0x4000aa9c(&local_a4c);
              param_11 = 0x400aaaf3;
              FUN_40004254((int *)&local_2a4,local_a4c,(undefined4 *)"TEMP.INI");
              param_11 = 0x400aab04;
              FUN_40004140(&local_a50,DAT_400e71f0);
              param_11 = local_a50;
              param_10 = "CheckPDF.exe ";
              param_9 = &DAT_400adae8;
              param_8 = local_128;
              param_7 = &DAT_400adae8;
              param_6 = &DAT_400ade34;
              param_5 = &DAT_400adae8;
              param_4 = local_2a4;
              FUN_4000aa6c(local_13c,&iStack_a54);
              FUN_4000aa6c(puStack_114,&local_a58);
              FUN_400042c8((int *)&local_128,0x11);
              puVar6 = puStack_114;
              pCVar15 = FUN_400043cc((undefined *)local_128);
              FUN_400b91f4(pCVar15,0,1,(int)puVar6);
              FUN_40004140((int *)&puStack_a5c,DAT_400e71f0);
              FUN_40004210((int *)&puStack_a5c,local_2a4);
              uVar10 = FUN_4000ad04(puStack_a5c);
              if ((char)uVar10 == '\0') {
                FUN_40004010((int *)&local_278,0x400addd0);
              }
              else {
                FUN_40004140((int *)&puStack_a60,DAT_400e71f0);
                FUN_40004210((int *)&puStack_a60,local_2a4);
                pcVar12 = FUN_400043cc(puStack_a60);
                FUN_40029834(DAT_400e7218,pcVar12);
                if (*(int *)(DAT_400e7218 + 0xc) < 1) {
                  FUN_40004010((int *)&local_278,0x400addd0);
                }
                else {
                  pcVar12 = (char *)FUN_4002934c(DAT_400e7218,0);
                  FUN_40004140((int *)&local_278,pcVar12);
                }
              }
              FUN_40004140((int *)&puStack_a64,DAT_400e71f0);
              FUN_40004210((int *)&puStack_a64,local_2a4);
              FUN_4000ae08(puStack_a64);
              FUN_40004140(&iStack_a6c,DAT_400e71f0);
              piVar21 = &iStack_a70;
              iVar16 = FUN_40004208((int)local_2a4);
              FUN_40004410((int)local_2a4,1,iVar16 - 4,piVar21);
              puVar5 = (uint *)&DAT_400ade40;
              FUN_400042c8((int *)&puStack_a68,3);
              FUN_4000ae08(puStack_a68);
              break;
            }
          }
          iVar16 = *in_FS_OFFSET;
          *in_FS_OFFSET = (int)&stack0xffffffc8;
          if ((DAT_400e71cc == (int *)0x0) ||
             ((**(code **)(*DAT_400e71cc + 0x10))(DAT_400e71cc,"FullText","QPDF_CHECKPDF"),
             cVar2 != '\0')) {
            (**(code **)(*DAT_400e71cc + 8))(DAT_400e71cc,"FullText","PDFExtractTime");
            FUN_40004140((int *)&puStack_a30,DAT_400e71f0);
            puStack_25c = (undefined1 *)FUN_400793f8((int)local_128,puStack_a30);
          }
          else {
            puStack_25c = (undefined1 *)FUN_40077b64((undefined *)local_128,(undefined *)0x0);
          }
          uVar18 = puStack_25c == (undefined1 *)0x0;
          if ((int)puStack_25c < 1) {
            FUN_40004010((int *)&local_278,0x400addd0);
          }
          else {
            FUN_40004010((int *)&local_278,0x400ad7b0);
          }
          FUN_40004318(local_278,(uint *)&DAT_400ad7b0);
          if ((bool)uVar18) {
            if (DAT_400e71cc == (int *)0x0) {
              local_13c = (undefined1 *)((int)&iRam00000000 + 1);
            }
            else {
              local_13c = (undefined1 *)
                          (**(code **)(*DAT_400e71cc + 8))(DAT_400e71cc,"FullText","PDFPageNumber");
            }
            if ((int)puStack_25c < (int)local_13c) {
              local_13c = puStack_25c;
            }
            if (DAT_400e71cc == (int *)0x0) {
              puStack_114 = &DAT_00000005;
            }
            else {
              puStack_114 = (undefined1 *)
                            (**(code **)(*DAT_400e71cc + 8))
                                      (DAT_400e71cc,"FullText","PDFExtractTime");
            }
            ppuVar38 = &puStack_a34;
            iVar16 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,1,iVar16 - 4,(int *)ppuVar38);
            FUN_40004254((int *)&local_140,puStack_a34,(undefined4 *)"qpdf.pdf");
            if ((DAT_400e71cc == (int *)0x0) ||
               ((**(code **)(*DAT_400e71cc + 0x10))(DAT_400e71cc,"FullText","QPDF_CHECKPDF"),
               (char)iVar16 != '\0')) {
              ppuVar37 = &puStack_25c;
              puVar6 = local_13c;
              puVar39 = puStack_114;
              FUN_40004140(&iStack_a38,DAT_400e71f0);
              iVar16 = FUN_40079108((undefined *)local_128,(undefined *)local_140,iStack_a38,
                                    ppuVar37,ppuVar37,puVar6,(int)puVar39);
              if (iVar16 == 0) {
                FUN_40004010((int *)&local_278,0x400ad7b0);
              }
              else {
                FUN_40004010((int *)&local_278,0x400addd0);
              }
            }
            else {
              iVar16 = FUN_40079624((undefined *)local_128,(undefined *)0x0,local_13c,
                                    (int *)&puStack_25c,(undefined1 *)((int)&iRam00000000 + 1),
                                    (undefined *)local_140);
              if (iVar16 == 0) {
                FUN_40004010((int *)&local_278,0x400ad7b0);
              }
              else {
                FUN_40004010((int *)&local_278,0x400addd0);
              }
            }
            FUN_4000aea0((undefined *)local_140,(int *)&puStack_a40);
            FUN_4000aa6c(local_13c,&iStack_a44);
            FUN_4000afc4((undefined *)local_140,&iStack_a48);
            FUN_400042c8((int *)&puStack_a3c,4);
            pCVar13 = FUN_400043cc(puStack_a3c);
            DeleteFileA(pCVar13);
            iVar16 = iStack_a48;
            puVar5 = puStack_a40;
          }
          *in_FS_OFFSET = iVar16;
        }
        break;
      case 0x5a:
        local_13c = (undefined1 *)FUN_4000ab48((byte *)local_128,1,extraout_ECX_68);
        pcVar12 = (char *)Irbisfield(param_1,(int)param_2,(int)local_13c,"");
        FUN_40004140((int *)&local_278,pcVar12);
      }
LAB_400ab751:
      pcVar12 = FUN_400043cc((undefined *)local_278);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x3f:
      func_0x40089060();
      break;
    case 0x40:
      piStack_284 = (int *)FUN_400031c8((int *)PTR_PTR_40011464,'\x01',extraout_ECX_39);
      *(undefined1 *)*param_4 = 0;
      FUN_40087fc0((int *)param_4,"0\r",(uint *)&DAT_400e7210);
      uVar10 = Irbismfn(param_1,(int)param_2);
      FUN_4000aa6c(uVar10,&iStack_678);
      uVar10 = func_0x4008941c(param_1,param_2);
      FUN_4000aa6c(uVar10,&iStack_67c);
      FUN_400042c8((int *)&puStack_674,4);
      pcVar12 = FUN_400043cc(puStack_674);
      FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      FUN_4000aa6c(*(undefined4 *)(*(int *)(*(int *)(*param_1 + 0x2c) + (int)param_2 * 0x43) + 0x18)
                   ,&iStack_684);
      uStack_50 = (double)CONCAT44(&UNK_400a52ec,(undefined *)uStack_50);
      FUN_400042c8((int *)&puStack_680,3);
      uStack_50 = (double)CONCAT44(&UNK_400a52f7,(undefined *)uStack_50);
      pcVar12 = FUN_400043cc(puStack_680);
      uStack_50 = (double)CONCAT44(&UNK_400a5306,(undefined *)uStack_50);
      FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      uStack_50 = (double)CONCAT44(&UNK_400a5311,(undefined *)uStack_50);
      local_13c = (undefined1 *)Irbisnfields(param_1,(int)param_2);
      if (0 < (int)local_13c) {
        puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
        puStack_2ec = local_13c;
        do {
          uStack_50._0_4_ = &UNK_400a5348;
          pcVar12 = (char *)Irbisfield(param_1,(int)param_2,(int)puStack_248,(char *)0x0);
          uStack_50._0_4_ = &UNK_400a5355;
          FUN_40004140((int *)&local_128,pcVar12);
          uStack_50._0_4_ = &UNK_400a5366;
          iStack_124 = Irbisfldtag(param_1,(int)param_2,(int)puStack_248);
          puStack_12c = (undefined1 *)0x0;
          uStack_50 = (double)CONCAT44(uStack_50._4_4_,&UNK_400a537f);
          iVar16 = FUN_40004208((int)local_128);
          if (0 < iVar16) {
            puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
            iStack_2f0 = iVar16;
            do {
              if (((char *)((int)local_128 + -1))[(int)puStack_114] == '^') {
                uStack_50 = (double)CONCAT44(uStack_50._4_4_,&UNK_400a53b1);
                iVar16 = FUN_400043d8((int *)&local_128);
                puStack_114[iVar16 + -1] = 0xd;
                puStack_12c = (undefined1 *)((int)&iRam00000000 + 1);
              }
              puStack_114 = puStack_114 + 1;
              iStack_2f0 = iStack_2f0 + -1;
            } while (iStack_2f0 != 0);
          }
          if (puStack_12c == (undefined1 *)((int)&iRam00000000 + 1)) {
            uStack_50._0_4_ = &UNK_400a53f2;
            (**(code **)(*piStack_284 + 0x2c))(piStack_284,local_128);
            uStack_50._0_4_ = &UNK_400a53fd;
            iVar16 = (**(code **)(*piStack_284 + 0x14))();
            if (iVar16 < 1) {
code_r0x400a5432:
              uStack_50 = (double)CONCAT44(uStack_50._4_4_,&UNK_400a543d);
              FUN_40003f78((int *)&local_128);
            }
            else {
              uStack_50._0_4_ = &UNK_400a5414;
              (**(code **)(*piStack_284 + 0xc))(piStack_284,0,&iStack_688);
              if (iStack_688 == 0) goto code_r0x400a5432;
              uStack_50 = (double)CONCAT44(uStack_50._4_4_,&UNK_400a5430);
              (**(code **)(*piStack_284 + 0xc))(piStack_284,0,&local_128);
            }
            uStack_50 = (double)CONCAT44(uStack_50._4_4_,&UNK_400a5448);
            iVar16 = (**(code **)(*piStack_284 + 0x14))();
            if (0 < iVar16 + -1) {
              puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
              iStack_2f0 = iVar16 + -1;
              do {
                uStack_50 = (double)CONCAT44(&UNK_400a5474,(undefined *)uStack_50);
                (**(code **)(*piStack_284 + 0xc))(piStack_284,puStack_114,&iStack_68c);
                uStack_50 = (double)CONCAT44(&UNK_400a547f,(undefined *)uStack_50);
                iVar16 = FUN_40004208(iStack_68c);
                if (1 < iVar16) {
                  uStack_50 = (double)CONCAT44(local_128,&DAT_400ad76c);
                  puStack_54 = &UNK_400a54a4;
                  (**(code **)(*piStack_284 + 0xc))(piStack_284,puStack_114,auStack_690);
                  uStack_50 = (double)CONCAT44(&UNK_400a54ba,(undefined *)uStack_50);
                  FUN_400042c8((int *)&local_128,3);
                }
                puStack_114 = puStack_114 + 1;
                iStack_2f0 = iStack_2f0 + -1;
              } while (iStack_2f0 != 0);
            }
          }
          if (local_128 != (uint *)0x0) {
            uStack_50 = (double)CONCAT44(&UNK_400a54e8,(undefined *)uStack_50);
            (**(code **)(*local_118 + 0x38))(local_118,local_128,iStack_124);
          }
          puStack_248 = puStack_248 + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      uStack_50 = (double)CONCAT44(&UNK_400a5505,(undefined *)uStack_50);
      FUN_40023098(local_118);
      uStack_50 = (double)CONCAT44(&UNK_400a5515,(undefined *)uStack_50);
      FUN_40004010((int *)&puStack_270,0x400adc3c);
      iStack_124 = 0;
      uStack_50 = (double)CONCAT44(&UNK_400a5528,(undefined *)uStack_50);
      puVar6 = (undefined1 *)(**(code **)(*local_118 + 0x14))();
      if (-1 < (int)(puVar6 + -1)) {
        puStack_248 = (undefined1 *)0x0;
        puStack_2ec = puVar6;
        do {
          (**(code **)(*local_118 + 0xc))(local_118,puStack_248,&local_128);
          iVar16 = (**(code **)(*local_118 + 0x18))(local_118,puStack_248);
          if (iVar16 == iStack_124) {
            puStack_25c = puStack_25c + 1;
          }
          else {
            uVar10 = (**(code **)(*local_118 + 0x18))(local_118,puStack_248);
            FUN_4000aa6c(uVar10,&iStack_694);
            FUN_400042c8((int *)&puStack_270,4);
            puStack_25c = (undefined1 *)0x0;
            iStack_124 = (**(code **)(*local_118 + 0x18))(local_118,puStack_248);
            FUN_40004210((int *)&puStack_270,(undefined4 *)&UNK_400adc3c);
          }
          FUN_4000aa6c(puStack_25c,&iStack_698);
          FUN_400042c8((int *)&puStack_270,5);
          FUN_40003f78((int *)&local_2a4);
          FUN_40004010(&iStack_26c,0x400ad760);
          puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_12c = (undefined1 *)0x0;
          do {
            if (((char *)((int)local_128 + -1))[(int)puStack_114] == '^') {
              iVar16 = FUN_40004208((int)local_128);
              if (iVar16 < (int)(puStack_114 + 1)) break;
              if (local_2a4 != (uint *)0x0) {
                uStack_50 = (double)CONCAT44(iStack_26c,&UNK_400adc48);
                puStack_54 = &DAT_400adae8;
                puStack_58 = local_2a4;
                puStack_5c = &UNK_400adc60;
                puStack_60 = &UNK_400a56c4;
                FUN_400042c8((int *)&puStack_270,7);
              }
              FUN_40003f78((int *)&local_2a4);
              FUN_40004120(&iStack_26c,
                           CONCAT31((int3)((uint)local_128 >> 8),
                                    *(char *)((int)local_128 + (int)puStack_114)));
              puStack_114 = puStack_114 + 2;
              puStack_12c = (undefined1 *)((int)&iRam00000000 + 1);
            }
            else {
              uVar17 = (undefined3)((uint)local_128 >> 8);
              if ((((char *)((int)local_128 + -1))[(int)puStack_114] == '\"') ||
                 (((char *)((int)local_128 + -1))[(int)puStack_114] == '\\')) {
                uStack_50 = (double)CONCAT44(&UNK_400a5742,(undefined *)uStack_50);
                FUN_40004120(&iStack_69c,
                             CONCAT31(uVar17,((char *)((int)local_128 + -1))[(int)puStack_114]));
                uStack_50 = (double)CONCAT44(iStack_69c,&UNK_400a5758);
                FUN_400042c8((int *)&local_2a4,3);
              }
              else {
                FUN_40004120((int *)&puStack_6a0,
                             CONCAT31(uVar17,((char *)((int)local_128 + -1))[(int)puStack_114]));
                FUN_40004210((int *)&local_2a4,puStack_6a0);
              }
              puStack_114 = puStack_114 + 1;
            }
            iVar16 = FUN_40004208((int)local_128);
          } while ((int)puStack_114 <= iVar16);
          if (local_2a4 != (uint *)0x0) {
            if (puStack_12c == (undefined1 *)((int)&iRam00000000 + 1)) {
              uStack_50 = (double)CONCAT44(iStack_26c,&UNK_400adc48);
              puStack_54 = &DAT_400adae8;
              puStack_58 = local_2a4;
              puStack_5c = &DAT_400adae8;
              puStack_60 = &UNK_400a57eb;
              FUN_400042c8((int *)&puStack_270,7);
            }
            else {
              uStack_50 = (double)CONCAT44(local_2a4,&DAT_400adae8);
              puStack_54 = &UNK_400a5813;
              FUN_400042c8((int *)&puStack_270,4);
            }
          }
          iVar16 = (**(code **)(*local_118 + 0x14))();
          if ((int)(puStack_248 + 1) < iVar16) {
            iVar16 = (**(code **)(*local_118 + 0x18))(local_118,puStack_248 + 1);
            if (iVar16 == iStack_124) {
              FUN_40004210((int *)&puStack_270,(undefined4 *)&UNK_400adc94);
            }
            else {
              FUN_40004210((int *)&puStack_270,(undefined4 *)&UNK_400adc88);
            }
          }
          else {
            FUN_40004210((int *)&puStack_270,(undefined4 *)&UNK_400adca0);
          }
          puStack_248 = puStack_248 + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      pcVar12 = FUN_400043cc(puStack_270);
      FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      FUN_400031f8(piStack_284);
      break;
    case 0x42:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      puStack_114 = (undefined1 *)0x0;
      puVar6 = (undefined1 *)FUN_40004208((int)local_278);
      if (0 < (int)puVar6) {
        local_13c = (undefined1 *)((int)&iRam00000000 + 1);
        puStack_2ec = puVar6;
        do {
          puStack_114 = puStack_114 + ((byte *)((int)local_278 + -1))[(int)local_13c];
          local_13c = local_13c + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      FUN_4000aa6c(puStack_114,(int *)&local_140);
      pcVar12 = FUN_400043cc((undefined *)local_140);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x43:
      func_0x4009998c();
      break;
    case 0x44:
      FUN_40004140((int *)&puStack_b10,*(char **)((int)param_1 + 0x7da));
      FUN_4000afc4(puStack_b10,(int *)&puStack_b0c);
      pcVar12 = FUN_400043cc(puStack_b0c);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x45:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      if (local_13c == (undefined1 *)0x0) {
        iVar16 = FUN_40004208((int)local_278);
        local_13c = (undefined1 *)(iVar16 + 1);
      }
      FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&pbStack_ba4);
      iStack_124 = FUN_4000ab48(pbStack_ba4,0,extraout_ECX_90);
      if (0 < iStack_124) {
        ppuVar36 = &local_278;
        uVar11 = FUN_40004208((int)local_278);
        uVar18 = local_13c + 1 == (undefined1 *)0x0;
        FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        FUN_40004318(local_278,(uint *)&DAT_400ad760);
        if ((bool)uVar18) {
          puStack_12c = param_6;
        }
        else {
          puStack_12c = (undefined1 *)FUN_4000ab48((byte *)local_278,1,extraout_ECX_91);
        }
        if (puStack_12c == (undefined1 *)0x0) {
          puStack_12c = (undefined1 *)((int)&iRam00000000 + 1);
        }
        local_13c = (undefined1 *)Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_12c);
        if (0 < (int)local_13c) {
          FUN_4000aa6c(local_13c,(int *)&puStack_ba8);
          pcVar12 = FUN_400043cc(puStack_ba8);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
      }
      break;
    case 0x46:
      DAT_400e31ec = 1;
      break;
    case 0x48:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      FUN_4009976c((int)local_278,(int *)&puStack_aec);
      pcVar12 = FUN_400043cc(puStack_aec);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x49:
      FUN_40004140((int *)&local_128,(char *)(param_5 + 2));
      iVar16 = FUN_40004208((int)local_128);
      if (iVar16 < 3) break;
      ppcVar33 = &pcStack_b6c;
      uVar11 = FUN_40004208((int)local_128);
      FUN_40004410((int)local_128,2,uVar11,(int *)ppcVar33);
      FUN_40004120((int *)&pcStack_b70,CONCAT31((int3)((uint)local_128 >> 8),(char)*local_128));
      local_13c = (undefined1 *)FUN_400044f4(pcStack_b70,pcStack_b6c);
      if ((int)local_13c < 1) break;
      uVar18 = local_13c + 1 == (undefined1 *)0x0;
      FUN_40004410((int)local_128,1,(uint)(local_13c + 1),(int *)&puStack_274);
      FUN_40004410((int)puStack_274,2,1,(int *)&puStack_b74);
      FUN_40004318(puStack_b74,(uint *)&DAT_400ad7b0);
      if ((bool)uVar18) {
code_r0x400ac693:
        func_0x40088110(puStack_274,0,&iStack_b7c);
        FUN_40004010((int *)&puStack_274,iStack_b7c);
      }
      else {
        FUN_40004410((int)puStack_274,2,1,(int *)&puStack_b78);
        FUN_40004318(puStack_b78,(uint *)&UNK_400adee0);
        if ((bool)uVar18) goto code_r0x400ac693;
      }
      piVar21 = &iStack_b80;
      uVar11 = FUN_40004208((int)local_128);
      FUN_40004410((int)local_128,(int)(local_13c + 2),uVar11,piVar21);
      puVar5 = (uint *)&UNK_400adefc;
      FUN_400042c8((int *)&local_128,7);
      pcVar12 = FUN_400043cc((undefined *)local_128);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x4b:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      func_0x40099d50(local_278,&puStack_af0);
      pcVar12 = FUN_400043cc(puStack_af0);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x4c:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      func_0x4009c5fc(local_278,&iStack_b84);
      FUN_40004010((int *)&local_140,iStack_b84);
      FUN_40003f78((int *)&local_128);
      do {
        puStack_248 = (undefined1 *)FUN_400044f4("%",(char *)local_140);
        if ((int)puStack_248 < 1) {
          FUN_40004010((int *)&local_128,(int)local_140);
        }
        else {
          FUN_40004410((int)local_140,1,(uint)(puStack_248 + -1),(int *)&local_b88);
          FUN_40004210((int *)&local_128,local_b88);
        }
        ppuVar36 = &local_140;
        uVar11 = FUN_40004208((int)local_140);
        FUN_40004410((int)local_140,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
        iVar16 = FUN_400044f4("%",(char *)local_140);
      } while ((0 < iVar16) && (local_140 != (uint *)0x0));
      pcVar12 = FUN_400043cc((undefined *)local_128);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x4d:
      puStack_248 = (undefined1 *)Irbisnocc(param_1,(int)param_2,0x3df);
      if (0 < (int)puStack_248) {
        local_13c = (undefined1 *)((int)&iRam00000000 + 1);
        puStack_2ec = puStack_248;
        do {
          pcVar12 = "";
          iVar16 = Irbisfieldn(param_1,(int)param_2,0x3df,1);
          Irbisfldrep(param_1,(int)param_2,iVar16,pcVar12);
          local_13c = local_13c + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      FUN_40004140(&iStack_b54,(char *)(param_5 + 2));
      (**(code **)(*local_118 + 0x2c))(local_118,iStack_b54);
      iVar16 = (**(code **)(*local_118 + 0x14))();
      if (-1 < iVar16 + -1) {
        local_13c = (undefined1 *)0x0;
        puStack_2ec = (undefined1 *)iVar16;
        do {
          iVar16 = 0;
          (**(code **)(*local_118 + 0xc))(local_118,local_13c,&puStack_b58);
          pcVar12 = FUN_400043cc(puStack_b58);
          Irbisfldadd(param_1,(int)param_2,0x3df,pcVar12,iVar16);
          local_13c = local_13c + 1;
          puStack_2ec = (undefined1 *)((int)puStack_2ec + -1);
        } while (puStack_2ec != (undefined1 *)0x0);
        puStack_2ec = (undefined1 *)0x0;
      }
      break;
    case 0x4e:
      uVar18 = param_5 + 2 == (byte *)0x0;
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      FUN_40004410((int)local_278,1,1,(int *)&pbStack_b18);
      FUN_4000a77c(pbStack_b18,(int *)&puStack_b14);
      FUN_40004318(puStack_b14,(uint *)&UNK_400ad77c);
      if ((bool)uVar18) {
        ppuVar36 = &local_278;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,2,uVar11,(int *)ppuVar36);
        local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_278);
        if (local_13c == (undefined1 *)0x0) {
          iVar16 = FUN_40004208((int)local_278);
          local_13c = (undefined1 *)(iVar16 + 1);
        }
        FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&pbStack_b1c);
        iStack_124 = FUN_4000ab48(pbStack_b1c,0,extraout_ECX_85);
        ppuVar24 = &puStack_b24;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar24);
        FUN_40026f28(puStack_b24,&iStack_b20);
        FUN_40004010((int *)&local_278,iStack_b20);
        puStack_114 = (undefined1 *)0x0;
        if (((-1 < iStack_124) &&
            (iVar16 = (**(code **)(*DAT_400e7224 + 0x14))(), iStack_124 < iVar16)) &&
           ((**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,iStack_124,&iStack_b28), iStack_b28 != 0
           )) {
          (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,iStack_124,&uStack_b2c);
          (**(code **)(*local_118 + 0x2c))(local_118,uStack_b2c);
          if (local_278 == (uint *)0x0) {
            puStack_114 = (undefined1 *)(**(code **)(*local_118 + 0x14))();
          }
          else {
            iVar16 = (**(code **)(*local_118 + 0x14))();
            if (-1 < iVar16 + -1) {
              local_13c = (undefined1 *)0x0;
              puStack_2ec = (undefined1 *)iVar16;
              do {
                (**(code **)(*local_118 + 0xc))(local_118,local_13c,&puStack_b34);
                FUN_40026f28(puStack_b34,(int *)&pcStack_b30);
                iVar16 = FUN_400044f4((char *)local_278,pcStack_b30);
                if (iVar16 != 0) {
                  puStack_114 = puStack_114 + 1;
                }
                local_13c = local_13c + 1;
                puStack_2ec = (undefined1 *)((int)puStack_2ec + -1);
              } while (puStack_2ec != (undefined1 *)0x0);
              puStack_2ec = (undefined1 *)0x0;
            }
          }
        }
      }
      else {
        FUN_40004410((int)local_278,1,1,(int *)&pbStack_b3c);
        FUN_4000a77c(pbStack_b3c,(int *)&puStack_b38);
        FUN_40004318(puStack_b38,(uint *)&UNK_400aded4);
        if ((bool)uVar18) {
          ppuVar36 = &local_278;
          uVar11 = FUN_40004208((int)local_278);
          FUN_40004410((int)local_278,2,uVar11,(int *)ppuVar36);
        }
        local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_278);
        if (local_13c == (undefined1 *)0x0) {
          iVar16 = FUN_40004208((int)local_278);
          local_13c = (undefined1 *)(iVar16 + 1);
        }
        FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&pbStack_b40);
        iStack_124 = FUN_4000ab48(pbStack_b40,0,extraout_ECX_86);
        ppuVar24 = &puStack_b48;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar24);
        FUN_40026f28(puStack_b48,&iStack_b44);
        FUN_40004010((int *)&local_278,iStack_b44);
        puVar6 = (undefined1 *)Irbisnocc(param_1,(int)param_2,iStack_124);
        puStack_114 = puVar6;
        if ((local_278 != (uint *)0x0) &&
           (puStack_114 = (undefined1 *)0x0, local_13c = puVar6, 0 < (int)puVar6)) {
          puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = puVar6;
          do {
            puVar5 = (uint *)&DAT_400ad770;
            iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_248);
            pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,(char *)puVar5);
            FUN_40004140((int *)&puStack_b4c,pcVar12);
            FUN_40026f28(puStack_b4c,(int *)&local_140);
            iVar16 = FUN_400044f4((char *)local_278,(char *)local_140);
            if (iVar16 != 0) {
              puStack_114 = puStack_114 + 1;
            }
            puStack_248 = puStack_248 + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
      }
      FUN_4000aa6c(puStack_114,(int *)&puStack_b50);
      pcVar12 = FUN_400043cc(puStack_b50);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x4f:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      func_0x4008e5ac(local_278,1,&puStack_ae4);
      pcVar12 = FUN_400043cc(puStack_ae4);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x50:
      func_0x4008982c();
      break;
    case 0x52:
      FUN_40004140((int *)&local_128,(char *)(param_5 + 2));
      puVar6 = (undefined1 *)FUN_40004208((int)local_128);
      if (0 < (int)puVar6) {
        do {
          local_13c = puVar6;
          if (((char *)((int)local_128 + -1))[(int)local_13c] == '.') {
            FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&puStack_ae8);
            pcVar12 = FUN_400043cc(puStack_ae8);
            FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
            break;
          }
          local_13c = local_13c + -1;
          puVar6 = local_13c;
        } while (local_13c != (undefined1 *)0x0);
      }
      break;
    case 0x53:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 3));
      while( true ) {
        local_13c = (undefined1 *)FUN_400044f4("<",(char *)local_278);
        puStack_248 = (undefined1 *)FUN_400044f4(">",(char *)local_278);
        if (((int)local_13c < 1) || ((int)puStack_248 <= (int)local_13c)) break;
        FUN_40004410((int)local_278,(int)(local_13c + 1),(uint)(puStack_248 + (-1 - (int)local_13c))
                     ,(int *)&local_128);
        ppuVar38 = &puStack_af4;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(puStack_248 + 1),uVar11,(int *)ppuVar38);
        puVar8 = puStack_af4;
        FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&puStack_af8);
        FUN_40004254((int *)&local_278,puStack_af8,puVar8);
        if (param_5[2] == 0x30) {
          puStack_248 = (undefined1 *)FUN_400044f4("=",(char *)local_128);
          if (puStack_248 == (undefined1 *)0x0) {
            FUN_40003f78((int *)&local_128);
          }
          else {
            ppuVar36 = &local_128;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
          }
        }
        else if (param_5[2] == 0x31) {
          puStack_248 = (undefined1 *)FUN_400044f4("=",(char *)local_128);
          if (puStack_248 == (undefined1 *)0x0) {
            FUN_40023740(&UNK_400adebc,&iStack_afc);
            FUN_40023740(&UNK_400adec8,&iStack_b00);
            FUN_400042c8((int *)&local_128,3);
          }
          else {
            FUN_40004410((int)local_128,1,(uint)(puStack_248 + -1),(int *)&local_128);
          }
        }
        FUN_40004410((int)local_278,1,(uint)(local_13c + -1),&iStack_b04);
        ppuVar36 = &puStack_b08;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)local_13c,uVar11,(int *)ppuVar36);
        puVar5 = puStack_b08;
        FUN_400042c8((int *)&local_278,3);
      }
      pcVar12 = FUN_400043cc((undefined *)local_278);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x54:
      func_0x40099944();
      break;
    case 0x55:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      FUN_40004410((int)local_278,1,(int)puStack_248 - 1,(int *)&local_140);
      ppuVar36 = &local_278;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)puStack_248 + 1,uVar11,(int *)ppuVar36);
      puStack_248 = (undefined1 *)FUN_4000ab48((byte *)local_140,0,extraout_ECX_88);
      FUN_40003f78((int *)&local_140);
      if ((0 < (int)puStack_248) && (0 < (int)puStack_248)) {
        puStack_2ec = puStack_248;
        local_13c = (undefined1 *)((int)&iRam00000000 + 1);
        do {
          FUN_40004210((int *)&local_140,local_278);
          local_13c = local_13c + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      pcVar12 = FUN_400043cc((undefined *)local_140);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x56:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      if ((int)puStack_248 < 1) {
        FUN_40003f78((int *)&puStack_274);
      }
      else {
        FUN_40004410((int)local_278,1,(uint)(puStack_248 + -1),(int *)&local_140);
        ppuVar36 = &local_278;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
        puStack_248 = (undefined1 *)FUN_4000ab48((byte *)local_140,0,extraout_ECX_87);
        FUN_40021570((undefined *)local_278,&local_b8c);
        FUN_400041d0((int *)&puStack_274,local_b8c);
        if ((int)puStack_248 < 1) {
          FUN_40003f78((int *)&puStack_274);
        }
        else {
          FUN_40004410((int)puStack_274,1,(uint)puStack_248,(int *)&puStack_274);
        }
        FUN_400047a8((BSTR)&local_b94,(LPCSTR)puStack_274);
        FUN_40021554(local_b94,&local_b90);
        FUN_40004010((int *)&puStack_274,local_b90);
      }
      pcVar12 = FUN_400043cc((undefined *)puStack_274);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x57:
      FUN_40003f78((int *)&local_128);
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      FUN_40004410((int)local_278,1,(int)puStack_248 - 1,(int *)&local_140);
      ppuVar36 = &local_278;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)puStack_248 + 1,uVar11,(int *)ppuVar36);
      puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      if (0 < (int)puStack_248) {
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
        FUN_40004410((int)local_278,1,(uint)(puStack_248 + -1),(int *)&local_278);
      }
      if (local_140 == (uint *)0x0) {
        FUN_40003f78((int *)&local_128);
      }
      else {
        FUN_40029500(DAT_400e7218);
        puStack_248 = (undefined1 *)FUN_400044f4("?",(char *)local_140);
        do {
          if (0 < (int)puStack_248) {
            FUN_40004410((int)local_140,1,(uint)(puStack_248 + -1),(int *)&puStack_274);
            ppuVar36 = &local_140;
            uVar11 = FUN_40004208((int)local_140);
            FUN_40004410((int)local_140,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
            if (puStack_274 != (uint *)0x0) {
              pcVar12 = FUN_400043cc((undefined *)puStack_274);
              FUN_40028c74(DAT_400e7218,pcVar12);
              puStack_248 = (undefined1 *)FUN_400044f4("?",(char *)local_140);
            }
          }
        } while (((puStack_248 != (undefined1 *)0x0) && (bVar20 = local_140 == (uint *)0x0, !bVar20)
                 ) && (FUN_40004318(local_140,(uint *)&UNK_400ad724), !bVar20));
        func_0x4009a1c0(DAT_400e7218,local_278,local_128);
        FUN_40004010((int *)&local_128,iStack_b68);
      }
      pcVar12 = FUN_400043cc((undefined *)local_128);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x58:
      FUN_40003f78((int *)&local_128);
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      FUN_40004410((int)local_278,1,(int)puStack_248 - 1,(int *)&local_140);
      ppuVar36 = &local_278;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)puStack_248 + 1,uVar11,(int *)ppuVar36);
      puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
      if (0 < (int)puStack_248) {
        ppuVar36 = &local_128;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
        FUN_40004410((int)local_278,1,(uint)(puStack_248 + -1),(int *)&local_278);
      }
      if (local_140 == (uint *)0x0) {
        FUN_40003f78((int *)&local_128);
      }
      else {
        FUN_40029500(DAT_400e7218);
        pcVar12 = FUN_400043cc((undefined *)local_140);
        FUN_4000b1a8((char *)*param_4,pcVar12);
        puStack_248 = (undefined1 *)Irbisfind((int)param_1,(char *)*param_4);
        while( true ) {
          ppcVar33 = &pcStack_b5c;
          uVar11 = FUN_40004208((int)local_140);
          FUN_40004140(&iStack_b60,(char *)*param_4);
          FUN_40004410(iStack_b60,1,uVar11,(int *)ppcVar33);
          iVar16 = FUN_4000a844(pcStack_b5c,(char *)local_140);
          if (iVar16 != 0) break;
          iVar16 = Irbisnposts((int)param_1);
          if (0 < iVar16) {
            iVar16 = FUN_40004208((int)local_140);
            FUN_40028c74(DAT_400e7218,(char *)(iVar16 + *param_4));
          }
          Irbisnxtterm((int)param_1,(char *)*param_4);
        }
        func_0x4009a1c0(DAT_400e7218,local_278,local_128);
        FUN_40004010((int *)&local_128,iStack_b64);
      }
      pcVar12 = FUN_400043cc((undefined *)local_128);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      break;
    case 0x5a:
      uVar11 = FUN_4000b140((char *)param_5);
      if (3 < uVar11) {
        if (param_5[2] == 0x30) {
          func_0x40007944();
        }
        else if (param_5[2] == 0x31) {
          func_0x40007c8c();
        }
      }
      break;
    case 0x5c:
      FUN_40004140((int *)&local_278,(char *)(param_5 + 2));
      iVar16 = FUN_40004208((int)local_278);
      if (1 < iVar16) {
        piVar21 = &iStack_b9c;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,2,uVar11,piVar21);
        FUN_40004120((int *)&pbStack_ba0,CONCAT31((int3)((uint)local_278 >> 8),(byte)*local_278));
        uVar10 = FUN_4000ab48(pbStack_ba0,0,extraout_ECX_89);
        func_0x40088110(iStack_b9c,uVar10,&iStack_b98);
        FUN_40004010((int *)&local_278,iStack_b98);
        pcVar12 = FUN_400043cc((undefined *)local_278);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
      break;
    case 0x7e:
      FUN_40004140((int *)&local_128,(char *)(param_5 + 2));
      *(undefined1 *)*param_4 = 0;
      if ((*(int *)((int)param_1 + 0x845) != 0) &&
         (iVar16 = FUN_400044f4(",",(char *)local_128), 0 < iVar16)) {
        ppbVar28 = &pbStack_63c;
        iVar16 = FUN_400044f4(",",(char *)local_128);
        FUN_40004410((int)local_128,1,iVar16 - 1,(int *)ppbVar28);
        local_13c = (undefined1 *)FUN_4000ab48(pbStack_63c,0,extraout_ECX_40);
        ppuVar36 = &local_128;
        iVar16 = FUN_400044f4(",",(char *)local_128);
        iVar16 = iVar16 + 1;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,iVar16,uVar11,(int *)ppuVar36);
        if (DAT_400e71cc == (int *)0x0) {
          FUN_40004010((int *)&local_2d0,0x400adbe0);
          uVar10 = extraout_ECX_42;
        }
        else {
          (**(code **)*DAT_400e71cc)(DAT_400e71cc,"FullText","MORPH");
          uVar10 = extraout_ECX_41;
        }
        piStack_2d8 = FUN_40029218((int *)PTR_DAT_400281e0,'\x01',uVar10);
        FUN_40089484((int *)&local_2d0,(int)piStack_2d8);
        piStack_2d4 = Irbisinit();
        pcVar12 = (char *)FUN_4002934c((int)piStack_2d8,0);
        FUN_40004140((int *)&puStack_640,pcVar12);
        FUN_40004210((int *)&puStack_640,local_2d0);
        pcVar12 = FUN_400043cc(puStack_640);
        local_11c = Irbisinitmst(piStack_2d4,pcVar12,1);
        if (local_11c == 0) {
          pcVar12 = (char *)FUN_4002934c((int)piStack_2d8,1);
          FUN_40004140((int *)&puStack_644,pcVar12);
          FUN_40004210((int *)&puStack_644,local_2d0);
          pcVar12 = FUN_400043cc(puStack_644);
          local_11c = Irbisinitterm((int)piStack_2d4,pcVar12);
        }
        FUN_400031f8(piStack_2d8);
        if (local_11c == 0) {
          piStack_2e4 = (int *)FUN_400031c8((int *)PTR_PTR_40011464,'\x01',extraout_ECX_43);
          piStack_2dc = (int *)FUN_400031c8((int *)PTR_PTR_40011464,'\x01',extraout_ECX_44);
          piStack_2e0 = (int *)FUN_400031c8((int *)PTR_PTR_40011464,'\x01',extraout_ECX_45);
          IrbisRecord(*(int **)((int)param_1 + 0x845),0,(int)local_13c);
          IrbisInitUACTAB(*(int *)((int)param_1 + 0x845));
          FUN_4007fe24(*(undefined4 *)((int)param_1 + 0x845),(undefined *)local_128,
                       (int)param_1 + 0x6c5,piStack_2e4);
          puStack_114 = (undefined1 *)0x0;
          while (iVar16 = (**(code **)(*piStack_2e4 + 0x14))(), (int)puStack_114 < iVar16) {
            (**(code **)(*piStack_2e4 + 0xc))(piStack_2e4,puStack_114,&puStack_64c);
            FUN_400237a8(puStack_64c,&iStack_648);
            iVar16 = FUN_40004208(iStack_648);
            if (iVar16 < 2) {
              (**(code **)(*piStack_2e4 + 0x44))(piStack_2e4,puStack_114);
            }
            else {
              puStack_114 = puStack_114 + 1;
            }
          }
          puVar6 = (undefined1 *)Irbisnocc(*(int **)((int)param_1 + 0x845),0,0x1b);
          if (0 < (int)puVar6) {
            puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
            puStack_2ec = puVar6;
            do {
              pcVar12 = "";
              iVar16 = Irbisfieldn(*(int **)((int)param_1 + 0x845),0,0x1b,(int)puStack_114);
              pcVar12 = (char *)Irbisfield(*(int **)((int)param_1 + 0x845),0,iVar16,pcVar12);
              FUN_40004140(&iStack_650,pcVar12);
              (**(code **)(*piStack_2dc + 0x34))(piStack_2dc,iStack_650);
              puStack_114 = puStack_114 + 1;
              puStack_2ec = puStack_2ec + -1;
            } while (puStack_2ec != (undefined1 *)0x0);
          }
          func_0x40086858(*(undefined4 *)((int)param_1 + 0x845),piStack_2d4,piStack_2e4);
          FUN_400031f8(piStack_2e4);
          FUN_400031f8(piStack_2dc);
          iVar16 = (**(code **)(*piStack_2e0 + 0x14))();
          if (iVar16 == 0) {
            local_13c = (undefined1 *)((int)&iRam00000000 + 1);
            do {
              (**(code **)(*piStack_2e0 + 0x1c))(piStack_2e0,&iStack_658);
              iVar16 = FUN_40004208(iStack_658);
              if (99 < iVar16) break;
              pcVar12 = "";
              uStack_50 = (double)CONCAT44(&UNK_400a500f,(undefined *)uStack_50);
              iVar16 = Irbisfieldn(*(int **)((int)param_1 + 0x845),0,0x1b,(int)local_13c);
              pcVar12 = (char *)Irbisfield(*(int **)((int)param_1 + 0x845),0,iVar16,pcVar12);
              FUN_40004140(&iStack_654,pcVar12);
              (**(code **)(*piStack_2e0 + 0x34))(piStack_2e0,iStack_654);
              local_13c = local_13c + 1;
              iVar16 = Irbisnocc(*(int **)((int)param_1 + 0x845),0,0x1b);
            } while ((int)local_13c < iVar16);
          }
          (**(code **)(*piStack_2e0 + 0x1c))(piStack_2e0,&puStack_65c);
          pcVar12 = FUN_400043cc(puStack_65c);
          FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          FUN_400031f8(piStack_2e0);
        }
        Irbisclose(piStack_2d4);
      }
    }
    break;
  case 0xb:
    func_0x4008eec8();
    break;
  case 0xd:
    DAT_400e31f0 = 1;
    break;
  case 0xf:
    FUN_40029500(DAT_400e7214);
    local_13c = (undefined1 *)Irbisnfields(param_1,(int)param_2);
    UStack_134 = 0;
    if (0 < (int)local_13c) {
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
      puStack_2ec = local_13c;
      local_c = param_2;
      local_8 = param_1;
      do {
        pcVar12 = (char *)Irbisfield(local_8,(int)local_c,(int)puStack_248,(char *)0x0);
        FUN_40004140((int *)&local_128,pcVar12);
        iVar16 = FUN_40004208((int)local_128);
        UStack_134 = UStack_134 + iVar16;
        iStack_124 = Irbisfldtag(local_8,(int)local_c,(int)puStack_248);
        if (iStack_124 == 0x3b9) {
          FUN_40004010((int *)&local_128,0x400ad68c);
        }
        FUN_4000aa6c(iStack_124,(int *)apuStack_334);
        pcVar12 = FUN_400043cc(apuStack_334[0]);
        puStack_12c = (undefined1 *)FUN_40028c04(DAT_400e7214,pcVar12);
        if ((int)puStack_12c < 0) {
          FUN_4000aa6c(iStack_124,(int *)&puStack_338);
          pcVar12 = FUN_400043cc(puStack_338);
          FUN_400299b4(DAT_400e7214,pcVar12,1);
          puStack_12c = (undefined1 *)((int)&iRam00000000 + 1);
        }
        else {
          iVar16 = FUN_4002993c(DAT_400e7214,(int)puStack_12c);
          FUN_40029978(DAT_400e7214,(int)puStack_12c,iVar16 + 1);
          puStack_12c = (undefined1 *)FUN_4002993c(DAT_400e7214,(int)puStack_12c);
        }
        FUN_4000aa6c(iStack_124,(int *)&piStack_340);
        local_8 = piStack_340;
        local_c = &DAT_400ad6b8;
        FUN_4000aa6c(puStack_12c,&iStack_344);
        FUN_400042c8((int *)&puStack_33c,5);
        pcVar12 = FUN_400043cc(puStack_33c);
        FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        pcVar12 = FUN_400043cc((undefined *)local_128);
        FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        FUN_40087fc0((int *)param_4,"\\par ",(uint *)&DAT_400e7210);
        puStack_248 = puStack_248 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    FUN_4000aa6c(local_13c,&iStack_34c);
    FUN_4000aa6c(UStack_134,&iStack_350);
    FUN_4000aa6c((int)local_13c * 0xc + UStack_134 + 0x20,(int *)&puStack_354);
    FUN_400042c8((int *)&puStack_348,6);
    pcVar12 = FUN_400043cc(puStack_348);
    FUN_40087fc0((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    puVar5 = puStack_354;
    break;
  case 0x10:
    FUN_40004140((int *)&local_278,(char *)param_5);
    local_13c = (undefined1 *)FUN_400044f4("?",(char *)local_278);
    if (0 < (int)local_13c) {
      FUN_40004410((int)local_278,2,(uint)(local_13c + -2),(int *)&local_140);
      uVar18 = local_13c + 1 == (undefined1 *)0x0;
      FUN_40004410((int)local_278,(int)(local_13c + 1),1,(int *)&puStack_358);
      FUN_40004318(puStack_358,(uint *)&UNK_400ad730);
      if ((bool)uVar18) {
        ppuVar36 = &local_278;
        uVar11 = FUN_40004208((int)local_278);
        uVar18 = local_13c + 2 == (undefined1 *)0x0;
        FUN_40004410((int)local_278,(int)(local_13c + 2),uVar11,(int *)ppuVar36);
      }
      else {
        ppuVar38 = &puStack_35c;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar38);
        FUN_40004254((int *)&local_278,(undefined4 *)&UNK_400ad73c,puStack_35c);
        puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_278);
        if (puStack_248 == (undefined1 *)0x0) {
          if (param_6 == (undefined1 *)0x0) {
            puStack_12c = (undefined1 *)((int)&iRam00000000 + 1);
          }
          else {
            puStack_12c = param_6;
          }
          iVar16 = FUN_40004208((int)local_278);
          puStack_248 = (undefined1 *)(iVar16 + 1);
        }
        else {
          ppbVar28 = &pbStack_360;
          uVar11 = FUN_40004208((int)local_278);
          FUN_40004410((int)local_278,(int)(puStack_248 + 1),uVar11,(int *)ppbVar28);
          puStack_12c = (undefined1 *)FUN_4000ab48(pbStack_360,param_6,extraout_ECX_00);
        }
        local_13c = (undefined1 *)FUN_400044f4(".",(char *)local_278);
        if (local_13c == (undefined1 *)0x0) {
          UStack_134 = 0;
          local_13c = puStack_248;
        }
        else {
          FUN_40004410((int)local_278,(int)(local_13c + 1),
                       (uint)(puStack_248 + (-1 - (int)local_13c)),(int *)&pbStack_364);
          UStack_134 = FUN_4000ab48(pbStack_364,0,extraout_ECX_01);
        }
        puStack_248 = (undefined1 *)FUN_400044f4("*",(char *)local_278);
        if (puStack_248 == (undefined1 *)0x0) {
          puStack_130 = (undefined1 *)0x0;
          puStack_248 = local_13c;
        }
        else {
          FUN_40004410((int)local_278,(int)(puStack_248 + 1),
                       (uint)(local_13c + (-1 - (int)puStack_248)),(int *)&pbStack_368);
          puStack_130 = (undefined1 *)FUN_4000ab48(pbStack_368,0,extraout_ECX_02);
        }
        local_13c = (undefined1 *)FUN_400044f4("^",(char *)local_278);
        if (local_13c == (undefined1 *)0x0) {
          uStack_11e = _DAT_400ad770;
          local_13c = puStack_248;
        }
        else {
          FUN_40004410((int)local_278,(int)(local_13c + 1),1,(int *)&pbStack_370);
          FUN_4000a77c(pbStack_370,(int *)&puStack_36c);
          FUN_4000b204((char *)&uStack_11e,puStack_36c);
        }
        FUN_40004410((int)local_278,3,(uint)(local_13c + -3),(int *)&pbStack_374);
        uVar18 = 1;
        iStack_124 = FUN_4000ab48(pbStack_374,0,extraout_ECX_03);
        FUN_40004410((int)local_278,2,1,(int *)&pbStack_37c);
        FUN_4000a77c(pbStack_37c,(int *)&puStack_378);
        FUN_40004318(puStack_378,(uint *)&UNK_400ad77c);
        if ((bool)uVar18) {
          FUN_40003f78((int *)&local_128);
          iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
          if (iStack_124 < iVar16) {
            (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,iStack_124,&local_128);
            puVar4 = FUN_400043cc((undefined *)local_128);
            (**(code **)(*local_118 + 0x6c))(local_118,puVar4);
            FUN_40003f78((int *)&local_128);
            if ((0 < (int)puStack_12c) &&
               (iVar16 = (**(code **)(*local_118 + 0x14))(), (int)puStack_12c <= iVar16)) {
              (**(code **)(*local_118 + 0xc))(local_118,puStack_12c + -1,&local_128);
            }
          }
          *(undefined1 *)*param_4 = 0;
          if ((local_128 != (uint *)0x0) &&
             (FUN_400041b8(&local_380,(char *)&uStack_11e,2), local_380 != 0)) {
            pcVar12 = FUN_400043cc((undefined *)local_128);
            iVar16 = FUN_400c8098(pcVar12,*(undefined4 **)
                                           (*(int *)(*param_1 + 0x2c) + 8 + (int)param_2 * 0x43),
                                  (char)uStack_11e);
            if (iVar16 == 0) {
              FUN_40004140((int *)&local_128,
                           *(char **)(*(int *)(*param_1 + 0x2c) + 8 + (int)param_2 * 0x43));
            }
            else {
              FUN_40003f78((int *)&local_128);
            }
          }
        }
        else {
          pcVar12 = (char *)&uStack_11e;
          iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_12c);
          pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,pcVar12);
          FUN_40004140((int *)&local_128,pcVar12);
        }
        uVar18 = local_128 == (uint *)0x0;
        if (!(bool)uVar18) {
          if (0 < (int)puStack_130) {
            FUN_40021570((undefined *)local_128,&pOStack_2b4);
            uVar11 = FUN_4000482c((int)pOStack_2b4);
            if ((int)uVar11 < (int)puStack_130) {
              puStack_130 = (undefined1 *)FUN_4000482c((int)pOStack_2b4);
            }
            ppiVar29 = &piStack_384;
            uVar11 = FUN_4000482c((int)pOStack_2b4);
            FUN_400049e0((int)pOStack_2b4,(int)(puStack_130 + 1),uVar11,(BSTR)ppiVar29);
            FUN_40021554(piStack_384,(int *)&local_128);
          }
          uVar18 = UStack_134 == 0;
          if (0 < (int)UStack_134) {
            FUN_40021570((undefined *)local_128,&pOStack_2b4);
            FUN_400049e0((int)pOStack_2b4,1,UStack_134,(BSTR)&local_388);
            FUN_40021554(local_388,(int *)&local_128);
          }
          pcVar12 = FUN_400043cc((undefined *)local_128);
          FUN_4000b1d0((char *)*param_4,pcVar12,_DAT_400e7210);
        }
        FUN_40004140((int *)&local_278,(char *)*param_4);
      }
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
      FUN_40004410((int)local_140,1,1,(int *)&local_144);
      pcVar12 = FUN_400043cc((undefined *)local_144);
      pcVar12 = (char *)FUN_400252c0(pcVar12,&DAT_400e6ec8);
      FUN_40004140((int *)&local_144,pcVar12);
      do {
        FUN_40004318(local_144,(uint *)&UNK_400ad788);
        if ((((bool)uVar18) || (FUN_40004318(local_144,(uint *)&UNK_400ad794), (bool)uVar18)) ||
           (FUN_40004318(local_144,(uint *)&UNK_400ad7a0), (bool)uVar18)) break;
        puStack_248 = puStack_248 + 1;
        FUN_40004410((int)local_140,(int)puStack_248,1,(int *)&local_144);
        puVar6 = (undefined1 *)FUN_40004208((int)local_140);
        uVar18 = puVar6 == puStack_248;
      } while ((int)puStack_248 < (int)puVar6);
      iVar16 = FUN_40004208((int)local_140);
      if (iVar16 <= (int)puStack_248) {
        puStack_248 = (undefined1 *)0x0;
      }
      if (0 < (int)puStack_248) {
        bVar20 = true;
        iStack_264 = 0;
        FUN_40004318(local_144,(uint *)&UNK_400ad788);
        if (bVar20) {
          ppuVar36 = &local_128;
          uVar11 = FUN_40004208((int)local_140);
          FUN_40004410((int)local_140,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
          FUN_40003f78((int *)&puStack_274);
        }
        else {
          FUN_40004318(local_144,(uint *)&UNK_400ad794);
          if (bVar20) {
            FUN_40003f78((int *)&local_128);
            ppuVar36 = &puStack_274;
            uVar11 = FUN_40004208((int)local_140);
            FUN_40004410((int)local_140,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
          }
          else {
            iVar16 = FUN_40004208((int)local_140);
            puStack_260 = (undefined1 *)(iVar16 - (int)puStack_248);
            uVar11 = (uint)puStack_260 & 0x80000001;
            if ((int)uVar11 < 0) {
              uVar11 = (uVar11 - 1 | 0xfffffffe) + 1;
            }
            if (uVar11 != 0) {
              iStack_264 = 1;
            }
            ppuVar36 = &local_128;
            iStack_38c = FUN_40004208((int)local_140);
            iStack_38c = iStack_38c - (int)puStack_248;
            uVar11 = FUN_40002cf0();
            FUN_40004410((int)local_140,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
            ppuVar36 = &puStack_274;
            uVar11 = FUN_40004208((int)local_140);
            iStack_38c = FUN_40004208((int)local_140);
            iStack_38c = iStack_38c - (int)puStack_248;
            iVar16 = FUN_40002cf0();
            FUN_40004410((int)local_140,(int)(puStack_248 + iVar16 + 1),uVar11,(int *)ppuVar36);
          }
        }
        if ((local_128 == (uint *)0x0) && (puStack_274 == (uint *)0x0)) {
          iStack_264 = 1;
        }
        uVar18 = puStack_248 + -1 == (undefined1 *)0x0;
        FUN_40004410((int)local_140,1,(uint)(puStack_248 + -1),(int *)&puStack_390);
        FUN_40004318(puStack_390,(uint *)&DAT_400ad760);
        if ((bool)uVar18) {
          puStack_130 = param_6;
          if ((int)param_6 < 1) {
            puStack_130 = (undefined1 *)((int)&iRam00000000 + 1);
          }
        }
        else {
          FUN_40004410((int)local_140,1,(uint)(puStack_248 + -1),(int *)&pbStack_394);
          puStack_130 = (undefined1 *)FUN_4000ab48(pbStack_394,0,extraout_ECX_04);
        }
        if (iStack_264 == 0) {
          FUN_40004410((int)local_140,(int)puStack_248,1,&iStack_39c);
          func_0x4008f30c(local_278,iStack_39c,local_128);
          pcVar12 = FUN_400043cc(puStack_398);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
      }
    }
    break;
  case 0x11:
    FUN_40004140((int *)&local_278,(char *)param_5);
    ppbVar28 = &pbStack_3a0;
    uVar11 = FUN_40004208((int)local_278);
    FUN_40004410((int)local_278,2,uVar11,(int *)ppbVar28);
    puStack_248 = (undefined1 *)FUN_4000ab48(pbStack_3a0,10,extraout_ECX_05);
    puStack_268 = (undefined1 *)Irbismaxmfn(param_1);
    FUN_4000aa6c(puStack_268,(int *)&local_278);
    local_13c = (undefined1 *)FUN_40004208((int)local_278);
    if ((int)local_13c < (int)puStack_248) {
      local_13c = puStack_248 + -(int)local_13c;
      if (0 < (int)local_13c) {
        puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
        puStack_2ec = local_13c;
        do {
          FUN_40004254((int *)&local_278,(undefined4 *)&DAT_400ad7b0,local_278);
          puStack_248 = puStack_248 + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
        puStack_2ec = (undefined1 *)0x0;
      }
    }
    else {
      FUN_40004410((int)local_278,1,(uint)puStack_248,(int *)&local_278);
    }
    pcVar12 = FUN_400043cc((undefined *)local_278);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x12:
    switch(param_5[1]) {
    case 0:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad7bc,(int *)&local_140,extraout_ECX_06);
      break;
    default:
      FUN_40003f78((int *)&local_140);
      break;
    case 0x30:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad7d0,(int *)&local_140,extraout_ECX_07);
      break;
    case 0x31:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad7e0,(int *)&local_140,extraout_ECX_08);
      break;
    case 0x32:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad7ec,(int *)&local_140,extraout_ECX_09);
      break;
    case 0x33:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad7f8,(int *)&local_140,extraout_ECX_10);
      break;
    case 0x34:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad804,(int *)&local_140,extraout_ECX_11);
      break;
    case 0x35:
      func_0x4000bf28();
      FUN_4000cbc8(&UNK_400ad7a0,(int *)&local_140,extraout_ECX_12);
      break;
    case 0x36:
      FUN_40004140((int *)&local_278,(char *)param_5);
      ppbVar28 = &pbStack_3a4;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,3,uVar11,(int *)ppbVar28);
      uVar10 = FUN_4000ab48(pbStack_3a4,0,extraout_ECX_13);
      switch(uVar10) {
      default:
        FUN_40004010((int *)&local_140,0x400ad8d0);
        break;
      case 1:
        FUN_40004010((int *)&local_140,0x400ad810);
        break;
      case 2:
        FUN_40004010((int *)&local_140,0x400ad820);
        break;
      case 3:
        FUN_40004010((int *)&local_140,0x400ad830);
        break;
      case 4:
        FUN_40004010((int *)&local_140,0x400ad840);
        break;
      case 5:
        FUN_40004010((int *)&local_140,0x400ad850);
        break;
      case 6:
        FUN_40004010((int *)&local_140,0x400ad85c);
        break;
      case 7:
        FUN_40004010((int *)&local_140,0x400ad86c);
        break;
      case 8:
        FUN_40004010((int *)&local_140,0x400ad87c);
        break;
      case 9:
        FUN_40004010((int *)&local_140,0x400ad88c);
        break;
      case 10:
        FUN_40004010((int *)&local_140,0x400ad8a0);
        break;
      case 0xb:
        FUN_40004010((int *)&local_140,0x400ad8b0);
        break;
      case 0xc:
        FUN_40004010((int *)&local_140,0x400ad8c0);
      }
      FUN_40023740((undefined *)local_140,&iStack_3a8);
      FUN_40004010((int *)&local_140,iStack_3a8);
      break;
    case 0x37:
      FUN_40004140((int *)&local_278,(char *)param_5);
      ppbVar28 = &pbStack_3ac;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,3,uVar11,(int *)ppbVar28);
      uVar10 = FUN_4000ab48(pbStack_3ac,0,extraout_ECX_14);
      switch(uVar10) {
      default:
        FUN_40004010((int *)&local_140,0x400ad8d0);
        break;
      case 1:
        FUN_40004010((int *)&local_140,0x400ad8e8);
        break;
      case 2:
        FUN_40004010((int *)&local_140,0x400ad8f8);
        break;
      case 3:
        FUN_40004010((int *)&local_140,0x400ad908);
        break;
      case 4:
        FUN_40004010((int *)&local_140,0x400ad918);
        break;
      case 5:
        FUN_40004010((int *)&local_140,0x400ad928);
        break;
      case 6:
        FUN_40004010((int *)&local_140,0x400ad934);
        break;
      case 7:
        FUN_40004010((int *)&local_140,0x400ad944);
        break;
      case 8:
        FUN_40004010((int *)&local_140,0x400ad954);
        break;
      case 9:
        FUN_40004010((int *)&local_140,0x400ad964);
        break;
      case 10:
        FUN_40004010((int *)&local_140,0x400ad978);
        break;
      case 0xb:
        FUN_40004010((int *)&local_140,0x400ad988);
        break;
      case 0xc:
        FUN_40004010((int *)&local_140,0x400ad998);
      }
      FUN_40023740((undefined *)local_140,&iStack_3b0);
      FUN_40004010((int *)&local_140,iStack_3b0);
      break;
    case 0x38:
      FUN_40004140((int *)&local_278,(char *)param_5);
      ppbVar28 = &pbStack_3b4;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,3,uVar11,(int *)ppbVar28);
      uVar10 = FUN_4000ab48(pbStack_3b4,0,extraout_ECX_15);
      switch(uVar10) {
      default:
        FUN_40004010((int *)&local_140,0x400ad8d0);
        break;
      case 1:
        FUN_40004010((int *)&local_140,0x400ad9a8);
        break;
      case 2:
        FUN_40004010((int *)&local_140,0x400ad9b8);
        break;
      case 3:
        FUN_40004010((int *)&local_140,0x400ad9cc);
        break;
      case 4:
        FUN_40004010((int *)&local_140,0x400ad9dc);
        break;
      case 5:
        FUN_40004010((int *)&local_140,0x400ad9ec);
        break;
      case 6:
        FUN_40004010((int *)&local_140,0x400ad9f8);
        break;
      case 7:
        FUN_40004010((int *)&local_140,0x400ada08);
        break;
      case 8:
        FUN_40004010((int *)&local_140,0x400ada18);
        break;
      case 9:
        FUN_40004010((int *)&local_140,0x400ada28);
        break;
      case 10:
        FUN_40004010((int *)&local_140,0x400ada3c);
        break;
      case 0xb:
        FUN_40004010((int *)&local_140,0x400ada4c);
        break;
      case 0xc:
        FUN_40004010((int *)&local_140,0x400ada60);
      }
      FUN_40023740((undefined *)local_140,&iStack_3b8);
      FUN_40004010((int *)&local_140,iStack_3b8);
      break;
    case 0x39:
      func_0x4000bf54();
      FUN_4000cb9c((int *)&local_140,extraout_EDX,extraout_ECX_16);
      break;
    case 0x41:
      break;
    case 0x42:
      ppuVar36 = &local_278;
      FUN_40004140(&iStack_3bc,(char *)param_5);
      uVar11 = FUN_40004208(iStack_3bc);
      FUN_40004140(&iStack_3c0,(char *)param_5);
      FUN_40004410(iStack_3c0,3,uVar11,(int *)ppuVar36);
      ppbVar28 = &local_3c4;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,10,uVar11,(int *)ppbVar28);
      iStack_38c = FUN_4000ab48(local_3c4,0,extraout_ECX_17);
      fStack_3d0 = (float10)iStack_38c;
      FUN_40004410((int)local_278,7,2,(int *)&pbStack_3d4);
      uVar10 = FUN_4000ab48(pbStack_3d4,1,extraout_ECX_18);
      uVar27 = (ushort)uVar10;
      FUN_40004410((int)local_278,5,2,(int *)&pbStack_3d8);
      uVar10 = FUN_4000ab48(pbStack_3d8,1,extraout_ECX_19);
      uVar25 = (ushort)uVar10;
      FUN_40004410((int)local_278,1,4,(int *)&pbStack_3dc);
      uVar11 = FUN_4000ab48(pbStack_3dc,1,extraout_ECX_20);
      FUN_4000bd28(uVar11,uVar25,uVar27);
      FUN_4000cbc8(&UNK_400ada74,(int *)&local_140,extraout_ECX_21);
      break;
    case 0x43:
      ppuVar36 = &local_278;
      FUN_40004140(&iStack_3e0,(char *)param_5);
      uVar11 = FUN_40004208(iStack_3e0);
      FUN_40004140(&iStack_3e4,(char *)param_5);
      FUN_40004410(iStack_3e4,3,uVar11,(int *)ppuVar36);
      FUN_40004410((int)local_278,7,2,(int *)&pbStack_3e8);
      uVar10 = FUN_4000ab48(pbStack_3e8,1,extraout_ECX_22);
      uVar27 = (ushort)uVar10;
      FUN_40004410((int)local_278,5,2,(int *)&pbStack_3ec);
      uVar10 = FUN_4000ab48(pbStack_3ec,1,extraout_ECX_23);
      uVar25 = (ushort)uVar10;
      FUN_40004410((int)local_278,1,4,(int *)&local_3f0);
      uVar11 = FUN_4000ab48(local_3f0,1,extraout_ECX_24);
      FUN_4000bd28(uVar11,uVar25,uVar27);
      uStack_3f8 = (double)in_ST0;
      FUN_40004410((int)local_278,0x10,2,(int *)&pbStack_3fc);
      uVar10 = FUN_4000ab48(pbStack_3fc,1,extraout_ECX_25);
      uVar27 = (ushort)uVar10;
      FUN_40004410((int)local_278,0xe,2,(int *)&pbStack_400);
      uVar10 = FUN_4000ab48(pbStack_400,1,extraout_ECX_26);
      uVar25 = (ushort)uVar10;
      FUN_40004410((int)local_278,10,4,(int *)&local_404);
      uVar11 = FUN_4000ab48(local_404,1,extraout_ECX_27);
      FUN_4000bd28(uVar11,uVar25,uVar27);
      FUN_40002cf0();
      func_0x4000aa9c(&local_140);
      break;
    case 0x4a:
      ppuVar36 = &local_278;
      FUN_40004140(&iStack_408,(char *)param_5);
      uVar11 = FUN_40004208(iStack_408);
      FUN_40004140(&iStack_40c,(char *)param_5);
      FUN_40004410(iStack_40c,3,uVar11,(int *)ppuVar36);
      func_0x4009ca30(local_278,&iStack_410);
      FUN_40004010((int *)&local_140,iStack_410);
      break;
    case 0x4d:
      ppuVar36 = &local_278;
      FUN_40004140(&iStack_414,(char *)param_5);
      uVar11 = FUN_40004208(iStack_414);
      FUN_40004140(&iStack_418,(char *)param_5);
      FUN_40004410(iStack_418,3,uVar11,(int *)ppuVar36);
      local_13c = (undefined1 *)FUN_400044f4(".",(char *)local_278);
      if (local_13c == (undefined1 *)0x0) {
        FUN_40004210((int *)&local_278,(undefined4 *)&DAT_400ad754);
        local_13c = (undefined1 *)FUN_40004208((int)local_278);
      }
      FUN_40004410((int)local_278,1,(uint)(local_13c + -1),&iStack_41c);
      piVar21 = &iStack_420;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,piVar21);
      iVar16 = FUN_40004208((int)local_278);
      FUN_4000aa6c(iVar16 - (int)local_13c,&iStack_424);
      FUN_400042c8((int *)&local_278,4);
      iVar16 = *in_FS_OFFSET;
      *in_FS_OFFSET = (int)&stack0xffffffb8;
      uStack_50 = (double)CONCAT44(&UNK_400a14f5,(undefined *)uStack_50);
      FUN_40028234((undefined *)local_278);
      uStack_50 = (double)in_ST0;
      puStack_54 = &UNK_400a150c;
      FUN_4000cbc8((byte *)"yyyymmdd hhnnss",(int *)&local_140,extraout_ECX_28);
      *in_FS_OFFSET = iVar16;
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x13:
    func_0x4008ab24();
    break;
  case 0x15:
    puStack_260 = DAT_400e71e8;
    FUN_40004140((int *)&puStack_428,*(char **)((int)param_1 + 0x7da));
    FUN_4000afc4(puStack_428,(int *)&local_128);
    local_13c = (undefined1 *)FUN_40089484((int *)&local_128,DAT_400e7214);
    if (local_13c == (undefined1 *)0x0) {
      piStack_110 = Irbisinit();
      pcVar12 = (char *)FUN_4002934c(DAT_400e7214,1);
      FUN_40004140((int *)&puStack_42c,pcVar12);
      FUN_40004210((int *)&puStack_42c,local_128);
      pcVar12 = FUN_400043cc(puStack_42c);
      puStack_248 = (undefined1 *)Irbisinitterm((int)piStack_110,pcVar12);
      pcVar12 = (char *)FUN_4002934c(DAT_400e7214,0);
      FUN_40004140((int *)&puStack_430,pcVar12);
      FUN_40004210((int *)&puStack_430,local_128);
      pcVar12 = FUN_400043cc(puStack_430);
      iVar16 = Irbisinitmst(piStack_110,pcVar12,5);
      puStack_248 = (undefined1 *)((int)puStack_248 + iVar16);
      if (puStack_248 == (undefined1 *)0x0) {
        uVar18 = 0;
        pcVar12 = (char *)FUN_4002934c(DAT_400e7214,0);
        FUN_40004140((int *)&puStack_434,pcVar12);
        FUN_40004210((int *)&puStack_434,local_128);
        puVar4 = FUN_400043cc(puStack_434);
        uVar22 = SUB42(puVar4,0);
        uVar23 = (undefined2)((uint)puVar4 >> 0x10);
        pcVar12 = (char *)FUN_4002934c(DAT_400e7214,0);
        FUN_40004140((int *)&puStack_438,pcVar12);
        FUN_40004210((int *)&puStack_438,local_128);
        pcVar12 = FUN_400043cc(puStack_438);
        IrbisInitInvContext(piStack_110,pcVar12,CONCAT22(uVar23,uVar22),uVar18);
        puStack_248 = (undefined1 *)Irbisnewrec(piStack_110,0);
        iVar16 = Irbismfn(param_1,(int)param_2);
        Irbischangemfn(piStack_110,0,iVar16);
        if (puStack_248 == (undefined1 *)0x0) {
          puStack_248 = (undefined1 *)Irbisnfields(param_1,(int)param_2);
          if (0 < (int)puStack_248) {
            local_13c = (undefined1 *)((int)&iRam00000000 + 1);
            puStack_2ec = puStack_248;
            do {
              pcStack_138 = (char *)Irbisfield(param_1,(int)param_2,(int)local_13c,"");
              iStack_124 = Irbisfldtag(param_1,(int)param_2,(int)local_13c);
              Irbisfldadd(piStack_110,0,iStack_124,pcStack_138,(int)local_13c);
              local_13c = local_13c + 1;
              puStack_2ec = puStack_2ec + -1;
            } while (puStack_2ec != (undefined1 *)0x0);
          }
          FUN_40004140((int *)&local_128,(char *)(param_5 + 1));
          puStack_248 = (undefined1 *)FUN_400044f4("#",(char *)local_128);
          if (puStack_248 == (undefined1 *)0x0) {
            FUN_40003f78((int *)&puStack_274);
          }
          else {
            ppuVar36 = &puStack_274;
            uVar11 = FUN_40004208((int)local_128);
            FUN_40004410((int)local_128,(int)puStack_248 + 1,uVar11,(int *)ppuVar36);
            FUN_40004410((int)local_128,1,(int)puStack_248 - 1,(int *)&local_128);
          }
          FUN_400237a8((undefined *)local_128,&iStack_43c);
          FUN_40004010((int *)&local_128,iStack_43c);
          pcVar12 = (char *)FUN_4002934c(DAT_400e7214,9);
          FUN_40004140(&iStack_440,pcVar12);
          puVar5 = local_128;
          FUN_400042c8((int *)&local_128,3);
          pcVar12 = FUN_400043cc((undefined *)local_128);
          puStack_248 = (undefined1 *)Irbis_InitPFT((int)piStack_110,pcVar12);
          if (puStack_248 == (undefined1 *)0x0) {
            if (puStack_274 != (uint *)0x0) {
              FUN_40004140(&iStack_448,*(char **)((int)piStack_110 + 0x812));
              func_0x4009d490(iStack_448,puStack_274,&iStack_444);
              FUN_40004010((int *)&local_128,iStack_444);
              iVar16 = FUN_40004208((int)local_128);
              if (*(int *)((int)piStack_110 + 0x816) < iVar16) {
                FUN_400029b0(*(int *)((int)piStack_110 + 0x812));
                iVar16 = FUN_40004208((int)local_128);
                puVar8 = FUN_4000a75c(iVar16 + 1);
                *(undefined4 **)((int)piStack_110 + 0x812) = puVar8;
                uVar10 = FUN_40004208((int)local_128);
                *(undefined4 *)((int)piStack_110 + 0x816) = uVar10;
              }
              pcVar12 = FUN_400043cc((undefined *)local_128);
              FUN_4000b1a8(*(char **)((int)piStack_110 + 0x812),pcVar12);
            }
            DAT_400e31f8 = 1;
            puVar5 = (uint *)&UNK_400adac0;
            puStack_248 = (undefined1 *)Irbis_Format(piStack_110,0,1);
            DAT_400e31f8 = 0;
          }
          if (puStack_248 == (undefined1 *)0x0) {
            FUN_40087f50((int *)param_4,*(char **)((int)piStack_110 + 0x80e),(uint *)&DAT_400e7210);
          }
          else {
            FUN_4000aa6c(puStack_248,(int *)&puStack_450);
            FUN_40004254((int *)&puStack_44c,(undefined4 *)"Format error ",puStack_450);
            pcVar12 = FUN_400043cc(puStack_44c);
            FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
          }
        }
      }
      Irbisclose(piStack_110);
    }
    DAT_400e71e8 = puStack_260;
    break;
  case 0x16:
    func_0x4008b014();
    break;
  case 0x17:
    func_0x4008b8f0();
    break;
  case 0x18:
    FUN_40004140((int *)&local_278,(char *)param_5);
    ppuVar36 = &local_140;
    uVar11 = FUN_40004208((int)local_278);
    FUN_40004410((int)local_278,2,uVar11,(int *)ppuVar36);
    puStack_248 = (undefined1 *)FUN_400044f4("\"",(char *)local_140);
    while (puStack_248 != (undefined1 *)0x0) {
      ppuVar36 = &local_128;
      uVar11 = FUN_40004208((int)local_140);
      FUN_40004410((int)local_140,(int)(puStack_248 + 1),uVar11,(int *)ppuVar36);
      FUN_40004410((int)local_140,1,(uint)(puStack_248 + -1),(int *)&puStack_454);
      FUN_40004254((int *)&local_140,puStack_454,local_128);
      puStack_248 = (undefined1 *)FUN_400044f4("\"",(char *)local_140);
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x19:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    local_13c = (undefined1 *)FUN_400044f4("#",(char *)local_278);
    if (0 < (int)local_13c) {
      ppCVar34 = &local_610;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppCVar34);
      FUN_400047a8((BSTR)&local_60c,local_610);
      FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&pCStack_618);
      FUN_400047a8((BSTR)&local_614,pCStack_618);
      func_0x40086f58(local_614,local_60c);
      if ((char)uVar11 == '\0') {
        FUN_40004010((int *)&local_128,0x400ad7b0);
      }
      else {
        FUN_40004010((int *)&local_128,0x400adb24);
      }
      pcVar12 = FUN_400043cc((undefined *)local_128);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    }
    break;
  case 0x1c:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    FUN_40004410((int)local_278,1,1,(int *)&local_128);
    if (local_128 != (uint *)0x0) {
      ppuVar36 = &local_278;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,2,uVar11,(int *)ppuVar36);
      local_13c = (undefined1 *)FUN_400044f4((char *)local_128,(char *)local_278);
      if (local_13c != (undefined1 *)0x0) {
        FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&local_128);
        ppuVar36 = &local_278;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
        FUN_40021570((undefined *)local_278,&pOStack_604);
        FUN_40021570((undefined *)local_128,&pOStack_608);
        func_0x400278e0(pOStack_608,pOStack_604);
        if ((char)uVar11 == '\0') {
          FUN_40004010((int *)&local_128,0x400ad7b0);
        }
        else {
          FUN_40004010((int *)&local_128,0x400adb24);
        }
        pcVar12 = FUN_400043cc((undefined *)local_128);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
    }
    break;
  case 0x1f:
    FUN_40004140(&iStack_638,(char *)(param_5 + 1));
    func_0x4009e3e4(iStack_638,&iStack_634);
    FUN_40004010((int *)&local_128,iStack_634);
    pcVar12 = FUN_400043cc((undefined *)local_128);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x20:
  case 0x2f:
    pcVar12 = (char *)FUN_400252c0((char *)param_5,&DAT_400e6ec8);
    FUN_40004140((int *)&local_278,pcVar12);
    pcVar12 = FUN_400043cc((undefined *)local_278);
    FUN_4000b1d0((char *)param_5,pcVar12,32000);
    puStack_248 = (undefined1 *)func_0x40027d00(&DAT_400ad748,local_278);
    if (puStack_248 == (undefined1 *)0x0) {
      puStack_12c = param_6;
      iVar16 = FUN_40004208((int)local_278);
      puStack_248 = (undefined1 *)(iVar16 + 1);
    }
    else {
      uVar18 = puStack_248 + 1 == (undefined1 *)0x0;
      FUN_40004410((int)local_278,(int)(puStack_248 + 1),1,(int *)&puStack_458);
      FUN_40004318(puStack_458,(uint *)&DAT_400ad760);
      if ((bool)uVar18) {
        puStack_12c = (undefined1 *)0xffffffff;
      }
      else {
        ppbVar28 = &pbStack_45c;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(puStack_248 + 1),uVar11,(int *)ppbVar28);
        puStack_12c = (undefined1 *)FUN_4000ab48(pbStack_45c,param_6,extraout_ECX_29);
      }
    }
    local_13c = (undefined1 *)func_0x40027d00(&DAT_400ad754,local_278);
    if (local_13c == (undefined1 *)0x0) {
      UStack_134 = 0;
      local_13c = puStack_248;
    }
    else {
      FUN_40004410((int)local_278,(int)(local_13c + 1),(uint)(puStack_248 + (-1 - (int)local_13c)),
                   (int *)&pbStack_460);
      UStack_134 = FUN_4000ab48(pbStack_460,0,extraout_ECX_30);
    }
    puStack_248 = (undefined1 *)func_0x40027d00(&DAT_400ad760,local_278);
    if ((puStack_248 == (undefined1 *)0x0) ||
       ((1 < (int)puStack_248 && (((byte *)((int)local_278 + -2))[(int)puStack_248] == 0x5e)))) {
      puStack_130 = (undefined1 *)0x0;
      puStack_248 = local_13c;
    }
    else {
      FUN_40004410((int)local_278,(int)(puStack_248 + 1),(uint)(local_13c + (-1 - (int)puStack_248))
                   ,(int *)&pbStack_464);
      puStack_130 = (undefined1 *)FUN_4000ab48(pbStack_464,0,extraout_ECX_31);
    }
    local_13c = (undefined1 *)FUN_400044f4("^",(char *)local_278);
    if (local_13c == (undefined1 *)0x0) {
      uStack_11e = _DAT_400ad770;
      local_13c = puStack_248;
    }
    else {
      FUN_40004410((int)local_278,(int)(local_13c + 1),1,(int *)&puStack_468);
      FUN_4000b204((char *)&uStack_11e,puStack_468);
    }
    FUN_40004410((int)local_278,3,(uint)(local_13c + -3),(int *)&local_46c);
    iStack_124 = FUN_4000ab48(local_46c,0,extraout_ECX_32);
    uVar10 = extraout_ECX_33;
    if (puStack_12c == (undefined1 *)0xffffffff) {
      puStack_12c = (undefined1 *)Irbisnocc(param_1,(int)param_2,iStack_124);
      uVar10 = extraout_ECX_34;
    }
    if (*param_5 == 0x50) {
      FUN_4008f078();
    }
    else {
      bVar1 = param_5[1];
      if (bVar1 == 0x44) {
code_r0x400a1f37:
        piStack_288 = FUN_4005713c((int *)PTR_PTR_40056a80,'\x01',uVar10);
        iVar16 = *in_FS_OFFSET;
        *in_FS_OFFSET = (int)&stack0xffffffc8;
        local_13c = (undefined1 *)Irbisnocc(param_1,(int)param_2,iStack_124);
        if (0 < (int)local_13c) {
          puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
          puStack_2ec = local_13c;
          do {
            pcVar12 = (char *)&uStack_11e;
            iVar3 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_248);
            pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar3,pcVar12);
            FUN_40004140((int *)&local_128,pcVar12);
            FUN_40021570((undefined *)local_128,&pOStack_478);
            (**(code **)(*piStack_288 + 0x38))(piStack_288,pOStack_478);
            puStack_248 = puStack_248 + 1;
            puStack_2ec = puStack_2ec + -1;
          } while (puStack_2ec != (undefined1 *)0x0);
        }
        (**(code **)(*piStack_288 + 0x90))();
        if ((0 < (int)puStack_12c) &&
           (iVar3 = (**(code **)(*piStack_288 + 0x14))(), (int)puStack_12c <= iVar3)) {
          if (param_5[1] == 0x44) {
            iVar3 = (**(code **)(*piStack_288 + 0x14))();
            puStack_12c = (undefined1 *)((iVar3 - (int)puStack_12c) + 1);
          }
          if ((int)UStack_134 < 1) {
            (**(code **)(*piStack_288 + 0xc))(piStack_288,puStack_12c + -1,&local_480);
            UStack_134 = FUN_4000482c(local_480);
          }
          else {
            (**(code **)(*piStack_288 + 0xc))(piStack_288,puStack_12c + -1,&pOStack_2b4);
            FUN_400049e0((int)pOStack_2b4,1,UStack_134,(BSTR)&iStack_47c);
            UStack_134 = FUN_4000482c(iStack_47c);
          }
          ppiVar29 = &piStack_488;
          (**(code **)(*piStack_288 + 0xc))(piStack_288,puStack_12c + -1,&local_48c);
          FUN_400049e0(local_48c,(int)puStack_130,UStack_134,(BSTR)ppiVar29);
          FUN_40021554(piStack_488,(int *)&local_484);
          pcVar12 = FUN_400043cc(local_484);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
        *in_FS_OFFSET = iVar16;
        FUN_400031f8(piStack_288);
        return;
      }
      if (bVar1 == 0x47) {
        FUN_40003f78((int *)&local_128);
        iVar16 = (**(code **)(*DAT_400e7224 + 0x14))();
        if (iStack_124 < iVar16) {
          (**(code **)(*DAT_400e7224 + 0xc))(DAT_400e7224,iStack_124,&local_128);
          puVar4 = FUN_400043cc((undefined *)local_128);
          (**(code **)(*local_118 + 0x6c))(local_118,puVar4);
          FUN_40003f78((int *)&local_128);
          if ((0 < (int)puStack_12c) &&
             (iVar16 = (**(code **)(*local_118 + 0x14))(), (int)puStack_12c <= iVar16)) {
            (**(code **)(*local_118 + 0xc))(local_118,puStack_12c + -1,&local_128);
          }
        }
        *(undefined1 *)*param_4 = 0;
        if ((local_128 != (uint *)0x0) &&
           (FUN_400041b8(&local_490,(char *)&uStack_11e,2), local_490 != 0)) {
          pcVar12 = FUN_400043cc((undefined *)local_128);
          iVar16 = FUN_400c8098(pcVar12,*(undefined4 **)
                                         (*(int *)(*param_1 + 0x2c) + 8 + (int)param_2 * 0x43),
                                (char)uStack_11e);
          if (iVar16 == 0) {
            FUN_40004140((int *)&local_128,
                         *(char **)(*(int *)(*param_1 + 0x2c) + 8 + (int)param_2 * 0x43));
          }
          else {
            FUN_40003f78((int *)&local_128);
          }
        }
        if (local_128 != (uint *)0x0) {
          if (0 < (int)puStack_130) {
            FUN_40021570((undefined *)local_128,&pOStack_2b4);
            uVar11 = FUN_4000482c((int)pOStack_2b4);
            if ((int)uVar11 < (int)puStack_130) {
              puStack_130 = (undefined1 *)FUN_4000482c((int)pOStack_2b4);
            }
            ppiVar29 = &piStack_494;
            uVar11 = FUN_4000482c((int)pOStack_2b4);
            FUN_400049e0((int)pOStack_2b4,(int)(puStack_130 + 1),uVar11,(BSTR)ppiVar29);
            FUN_40021554(piStack_494,(int *)&local_128);
          }
          if (0 < (int)UStack_134) {
            FUN_40021570((undefined *)local_128,&pOStack_2b4);
            FUN_400049e0((int)pOStack_2b4,1,UStack_134,(BSTR)&local_498);
            FUN_40021554(local_498,(int *)&local_128);
          }
        }
        pcVar12 = FUN_400043cc((undefined *)local_128);
        FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      }
      else {
        if (bVar1 == 0x49) goto code_r0x400a1f37;
        if (bVar1 == 0x56) {
          pcVar12 = (char *)&uStack_11e;
          iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_12c);
          pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,pcVar12);
          FUN_40004140((int *)&local_128,pcVar12);
          if (local_128 != (uint *)0x0) {
            if (0 < (int)puStack_130) {
              FUN_40021570((undefined *)local_128,&pOStack_2b4);
              uVar11 = FUN_4000482c((int)pOStack_2b4);
              if ((int)uVar11 < (int)puStack_130) {
                puStack_130 = (undefined1 *)FUN_4000482c((int)pOStack_2b4);
              }
              ppiVar29 = &piStack_470;
              uVar11 = FUN_4000482c((int)pOStack_2b4);
              FUN_400049e0((int)pOStack_2b4,(int)(puStack_130 + 1),uVar11,(BSTR)ppiVar29);
              FUN_40021554(piStack_470,(int *)&local_128);
            }
            if (0 < (int)UStack_134) {
              FUN_40021570((undefined *)local_128,&pOStack_2b4);
              FUN_400049e0((int)pOStack_2b4,1,UStack_134,(BSTR)&piStack_474);
              FUN_40021554(piStack_474,(int *)&local_128);
            }
          }
          pcVar12 = FUN_400043cc((undefined *)local_128);
          FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
        }
      }
    }
    break;
  case 0x21:
    FUN_4008eb74();
    break;
  case 0x22:
    FUN_40004140((int *)&local_278,(char *)param_5);
    FUN_40004410((int)local_278,2,2,(int *)&puStack_4ac);
    FUN_40004318(puStack_4ac,(uint *)&UNK_400adaf4);
    if (((bool)uVar18) && (iVar16 = FUN_40004208((int)local_278), 0xd < iVar16)) {
      piVar21 = &local_4b0;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,2,uVar11,piVar21);
      func_0x40087c80(local_4b0,&local_140);
    }
    else {
      puStack_260 = (undefined1 *)0x0;
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 2);
      puStack_268 = (undefined1 *)0x0;
      iVar16 = FUN_40004208((int)local_278);
      if (iVar16 < 0xb) {
        local_13c = (undefined1 *)0x8;
      }
      else {
        local_13c = (undefined1 *)0xa;
      }
      while (uVar18 = puStack_260 == (undefined1 *)0x0, (bool)uVar18) {
        uVar19 = 0;
        FUN_40004410((int)local_278,(int)puStack_248,1,(int *)&local_128);
        FUN_40004318(local_128,(uint *)&UNK_400adb00);
        if (!(bool)uVar18) {
          FUN_40004318(local_128,(uint *)&UNK_400adb0c);
          if ((bool)uVar18) {
            puStack_268 = puStack_268 + (int)local_13c * 10;
          }
          else {
            FUN_40004318(local_128,(uint *)&UNK_400adb18);
            if ((!(bool)uVar19 && !(bool)uVar18) ||
               (FUN_40004318(local_128,(uint *)&DAT_400ad7b0), (bool)uVar19)) {
              puStack_260 = (undefined1 *)((int)&iRam00000000 + 1);
              puStack_268 = (undefined1 *)0x0;
            }
            else {
              iVar16 = FUN_4000ab0c((byte *)local_128);
              puStack_268 = puStack_268 + iVar16 * (int)local_13c;
            }
          }
          local_13c = local_13c + -1;
          if ((int)local_13c < 1) {
            puStack_260 = (undefined1 *)((int)&iRam00000000 + 1);
          }
        }
        puStack_248 = puStack_248 + 1;
      }
      if (puStack_268 == (undefined1 *)0x0) {
        FUN_40004010((int *)&local_140,0x400adb24);
      }
      else {
        puStack_248 = (undefined1 *)((int)puStack_268 / 0xb);
        if ((int)puStack_248 * 0xb - (int)puStack_268 == 0) {
          FUN_40004010((int *)&local_140,0x400ad7b0);
        }
        else {
          FUN_40004010((int *)&local_140,0x400adb24);
        }
      }
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x23:
    func_0x4008a31c();
    break;
  case 0x24:
    local_13c = (undefined1 *)(param_5[1] - 0x30);
    FUN_4000b1d0((char *)param_5,(char *)(param_5 + 2),32000);
    FUN_40087f50((int *)param_4,(char *)param_5,(uint *)&DAT_400e7210);
    pbStack_280 = param_5;
    while (0 < (int)local_13c) {
      pbStack_280 = (byte *)FUN_4000b37c((char *)pbStack_280," ");
      if (pbStack_280 == (byte *)0x0) {
        local_13c = (undefined1 *)0x0;
      }
      else {
        local_13c = local_13c + -1;
        if (local_13c == (undefined1 *)0x0) {
          FUN_40002b84((undefined4 *)param_5,(undefined4 *)*param_4,(int)pbStack_280 - (int)param_5)
          ;
          pbStack_280[*param_4 - (int)param_5] = 0;
        }
        else {
          pbStack_280 = pbStack_280 + 1;
        }
      }
    }
    break;
  case 0x25:
    local_13c = (undefined1 *)(param_5[1] - 0x30);
    FUN_4000b1d0((char *)param_5,(char *)(param_5 + 2),32000);
    pbStack_280 = param_5;
    while (0 < (int)local_13c) {
      pbStack_280 = (byte *)FUN_4000b37c((char *)pbStack_280," ");
      if (pbStack_280 == (byte *)0x0) {
        local_13c = (undefined1 *)0x0;
      }
      else {
        local_13c = local_13c + -1;
        if (local_13c == (undefined1 *)0x0) {
          FUN_40087f50((int *)param_4,(char *)(pbStack_280 + 1),(uint *)&DAT_400e7210);
        }
        else {
          pbStack_280 = pbStack_280 + 1;
        }
      }
    }
    break;
  case 0x26:
    FUN_40004140((int *)&local_278,(char *)param_5);
    FUN_40021570((undefined *)local_278,&pOStack_2b4);
    FUN_400049e0((int)pOStack_2b4,3,1,(BSTR)&piStack_2bc);
    ppOVar30 = &pOStack_2b4;
    uVar11 = FUN_4000482c((int)pOStack_2b4);
    FUN_400049e0((int)pOStack_2b4,4,uVar11,(BSTR)ppOVar30);
    FUN_40004944(piStack_2bc,(int *)&UNK_400adb30);
    if (((bool)uVar18) || (FUN_40004944(piStack_2bc,(int *)&UNK_400adb38), (bool)uVar18)) {
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
      local_13c = (undefined1 *)0x0;
      iStack_264 = 0;
      do {
        uVar18 = 0;
        uVar19 = true;
        FUN_40004944((int *)pOStack_2b4,(int *)0x0);
        if ((bool)uVar19) break;
        FUN_400049e0((int)pOStack_2b4,(int)puStack_248,1,(BSTR)&local_2c0);
        FUN_40004944(piStack_2bc,(int *)&UNK_400adb30);
        if ((bool)uVar19) {
          FUN_40004944((int *)local_2c0,(int *)&UNK_400adb40);
          if ((!(bool)uVar18) &&
             (FUN_40004944((int *)local_2c0,(int *)&UNK_400adb48), (bool)uVar18 || (bool)uVar19)) {
            local_13c = puStack_248;
            iStack_264 = 1;
          }
        }
        else {
          bVar20 = FUN_400206c0(*local_2c0);
          if (bVar20) {
            local_13c = puStack_248;
            iStack_264 = 1;
          }
        }
        puStack_248 = puStack_248 + 1;
        uVar11 = FUN_4000482c((int)pOStack_2b4);
        if ((int)uVar11 < (int)puStack_248) {
          iStack_264 = 1;
        }
      } while (iStack_264 == 0);
    }
    else {
      local_13c = (undefined1 *)FUN_40004a2c((short *)piStack_2bc,pOStack_2b4);
    }
    if (local_13c == (undefined1 *)0x0) {
      if ((byte)(param_5[1] - 0x30) < 5) {
        FUN_40004660(&pOStack_2b8,pOStack_2b4);
      }
      else if ((byte)(param_5[1] + 0xbf) < 5) {
        FUN_40004624(&pOStack_2b8);
      }
    }
    else {
      switch(param_5[1]) {
      case 0x30:
      case 0x41:
        FUN_400049e0((int)pOStack_2b4,1,(UINT)(local_13c + -1),(BSTR)&pOStack_2b8);
        break;
      case 0x31:
      case 0x42:
        ppOVar31 = &pOStack_2b8;
        uVar11 = FUN_4000482c((int)pOStack_2b4);
        FUN_400049e0((int)pOStack_2b4,(int)local_13c,uVar11,(BSTR)ppOVar31);
        break;
      case 0x32:
      case 0x43:
        ppOVar31 = &pOStack_2b8;
        uVar11 = FUN_4000482c((int)pOStack_2b4);
        FUN_400049e0((int)pOStack_2b4,(int)(local_13c + 1),uVar11,(BSTR)ppOVar31);
        break;
      case 0x33:
      case 0x44:
        FUN_40004624(&pOStack_2b8);
        puVar6 = (undefined1 *)FUN_4000482c((int)pOStack_2b4);
        uVar18 = puVar6 == (undefined1 *)((int)&iRam00000000 + 1);
        if (0 < (int)puVar6) {
          do {
            local_13c = puVar6;
            FUN_4000472c((BSTR)&piStack_4b4,
                         CONCAT22((short)((uint)pOStack_2b4 >> 0x10),
                                  pOStack_2b4[(int)(local_13c + -1)]));
            FUN_40004944(piStack_4b4,piStack_2bc);
            if ((bool)uVar18) break;
            FUN_4000472c((BSTR)&puStack_4b8,
                         CONCAT22((short)((uint)pOStack_2b4 >> 0x10),
                                  pOStack_2b4[(int)(local_13c + -1)]));
            FUN_40004898(&pOStack_2b8,puStack_4b8,(undefined4 *)pOStack_2b8);
            local_13c = local_13c + -1;
            uVar18 = local_13c == (undefined1 *)0x0;
            puVar6 = local_13c;
          } while (!(bool)uVar18);
        }
        break;
      case 0x34:
      case 0x45:
        FUN_40004660(&pOStack_2b8,pOStack_2b4);
        puVar6 = (undefined1 *)FUN_4000482c((int)pOStack_2b4);
        uVar18 = puVar6 == (undefined1 *)((int)&iRam00000000 + 1);
        if (0 < (int)puVar6) {
          do {
            local_13c = puVar6;
            FUN_4000472c((BSTR)&piStack_4bc,
                         CONCAT22((short)((uint)pOStack_2b4 >> 0x10),
                                  pOStack_2b4[(int)(local_13c + -1)]));
            FUN_40004944(piStack_4bc,piStack_2bc);
            if ((bool)uVar18) break;
            ppOVar31 = &pOStack_2b8;
            uVar11 = FUN_4000482c((int)pOStack_2b8);
            FUN_400049e0((int)pOStack_2b8,1,uVar11 - 1,(BSTR)ppOVar31);
            local_13c = local_13c + -1;
            uVar18 = local_13c == (undefined1 *)0x0;
            puVar6 = local_13c;
          } while (!(bool)uVar18);
        }
        break;
      case 0x35:
        FUN_40004660(&pOStack_2b8,pOStack_2b4);
        puVar6 = (undefined1 *)FUN_4000482c((int)pOStack_2b4);
        uVar18 = puVar6 == (undefined1 *)((int)&iRam00000000 + 1);
        if (0 < (int)puVar6) {
          do {
            local_13c = puVar6;
            FUN_4000472c((BSTR)&local_4c0,
                         CONCAT22((short)((uint)pOStack_2b4 >> 0x10),
                                  pOStack_2b4[(int)(local_13c + -1)]));
            FUN_40004944(local_4c0,piStack_2bc);
            if ((bool)uVar18) {
              ppOVar31 = &pOStack_2b8;
              uVar11 = FUN_4000482c((int)pOStack_2b8);
              FUN_400049e0((int)pOStack_2b8,1,uVar11 - 1,(BSTR)ppOVar31);
              break;
            }
            ppOVar31 = &pOStack_2b8;
            uVar11 = FUN_4000482c((int)pOStack_2b8);
            FUN_400049e0((int)pOStack_2b8,1,uVar11 - 1,(BSTR)ppOVar31);
            local_13c = local_13c + -1;
            uVar18 = local_13c == (undefined1 *)0x0;
            puVar6 = local_13c;
          } while (!(bool)uVar18);
        }
      }
    }
    FUN_40021554((int *)pOStack_2b8,(int *)&local_140);
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x27:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    func_0x40099874(local_278,&puStack_5a0);
    pcVar12 = FUN_400043cc(puStack_5a0);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x28:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    FUN_40003f78((int *)&local_128);
    FUN_40003f78((int *)&puStack_274);
    FUN_40003f78((int *)&local_144);
    local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_278);
    if (local_13c != (undefined1 *)0x0) {
      FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&local_128);
      ppuVar36 = &local_278;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
      local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_278);
      if (local_13c != (undefined1 *)0x0) {
        FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&puStack_274);
        ppuVar36 = &local_144;
        uVar11 = FUN_40004208((int)local_278);
        FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
      }
    }
    uVar18 = DAT_400e71cc == (int *)0x0;
    if ((bool)uVar18) {
      FUN_40003f78((int *)&local_140);
    }
    else {
      (**(code **)*DAT_400e71cc)(DAT_400e71cc,local_128,puStack_274);
    }
    FUN_40004410((int)local_140,1,1,(int *)&puStack_5c4);
    FUN_40004318(puStack_5c4,(uint *)&UNK_400adba8);
    if ((bool)uVar18) {
      pcVar12 = FUN_400043cc((undefined *)local_140);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    }
    else {
      FUN_40023740((undefined *)local_140,(int *)&puStack_5c8);
      pcVar12 = FUN_400043cc(puStack_5c8);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    }
    break;
  case 0x29:
    FUN_40003f78((int *)&local_140);
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_278);
    if (0 < (int)local_13c) {
      FUN_40004410((int)local_278,1,(uint)(local_13c + -1),(int *)&puStack_274);
      if (puStack_274 == (uint *)0x0) {
        FUN_40004140((int *)&puStack_5cc,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(puStack_5cc,(int *)&puStack_274);
      }
      if ((puStack_274 == (uint *)0x0) || ((char)*puStack_274 != '+')) {
        cStack_2e5 = '\0';
      }
      else {
        ppuVar36 = &puStack_274;
        iVar16 = FUN_40004208((int)puStack_274);
        FUN_40004410((int)puStack_274,2,iVar16 - 1,(int *)ppuVar36);
        cStack_2e5 = '\x01';
        if (puStack_274 == (uint *)0x0) {
          FUN_40004140((int *)&puStack_5d0,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_5d0,(int *)&puStack_274);
        }
      }
      ppuVar36 = &local_144;
      uVar11 = FUN_40004208((int)local_278);
      uVar18 = local_13c + 1 == (undefined1 *)0x0;
      FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
      pcVar12 = FUN_400043cc((undefined *)local_144);
      pcVar12 = (char *)FUN_400252c0(pcVar12,&DAT_400e6ec8);
      FUN_40004140((int *)&local_144,pcVar12);
      FUN_40004140((int *)&puStack_5d8,*(char **)((int)param_1 + 0x7da));
      FUN_4000afc4(puStack_5d8,(int *)&puStack_5d4);
      FUN_40004318(puStack_5d4,puStack_274);
      piStack_110 = param_1;
      if (!(bool)uVar18 || cStack_2e5 != '\0') {
        piStack_110 = Irbisinit();
        FUN_40089484((int *)&puStack_274,DAT_400e7214);
        if (cStack_2e5 == '\0') {
          pcVar12 = (char *)FUN_4002934c(DAT_400e7214,1);
          FUN_40004140((int *)&puStack_5e4,pcVar12);
          FUN_40004210((int *)&puStack_5e4,puStack_274);
          pcVar12 = FUN_400043cc(puStack_5e4);
          Irbisinitterm((int)piStack_110,pcVar12);
        }
        else {
          pcVar12 = (char *)FUN_4002934c(DAT_400e7214,1);
          FUN_40004140(&iStack_5e0,pcVar12);
          FUN_400042c8((int *)&puStack_5dc,3);
          pcVar12 = FUN_400043cc(puStack_5dc);
          Irbisinitterm((int)piStack_110,pcVar12);
        }
      }
      if (puStack_274 != (uint *)0x0) {
        FUN_400235ec(local_144,0xfe,&iStack_5e8);
        FUN_40004010((int *)&local_144,iStack_5e8);
        pcVar12 = FUN_400043cc((undefined *)local_144);
        FUN_4000b1d0(acStack_10c,pcVar12,0xfe);
        local_13c = (undefined1 *)Irbisfind((int)piStack_110,acStack_10c);
        if ((local_13c == (undefined1 *)0x0) &&
           (puStack_248 = (undefined1 *)Irbisnposts((int)piStack_110), -1 < (int)puStack_248)) {
          FUN_4000aa6c(puStack_248,(int *)&local_140);
        }
      }
      if (piStack_110 != param_1) {
        Irbisclose(piStack_110);
      }
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x2a:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    func_0x4008e5ac(local_278,0,&puStack_5a4);
    pcVar12 = FUN_400043cc(puStack_5a4);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x2b:
    FUN_40003f78((int *)&local_140);
    FUN_400252c0((char *)param_5,&DAT_400e6ec8);
    FUN_40004140((int *)&local_278,(char *)param_5);
    ppuVar36 = &local_278;
    uVar11 = FUN_40004208((int)local_278);
    FUN_40004410((int)local_278,2,uVar11,(int *)ppuVar36);
    piStack_110 = Irbisinit();
    iVar16 = Irbisinitterm((int)piStack_110,*(char **)((int)param_1 + 0x7de));
    if (iVar16 == 0) {
      local_13c = (undefined1 *)Irbisfind((int)piStack_110,(char *)(param_5 + 1));
      if ((local_13c == (undefined1 *)0xffffff35) ||
         (iVar16 = Irbisnposts((int)piStack_110), 0 < iVar16)) {
        if ((local_13c == (undefined1 *)0xffffff35) &&
           (iVar16 = Irbisnposts((int)piStack_110), iVar16 < 1)) {
          param_5[1] = 0;
        }
      }
      else {
        do {
          local_13c = (undefined1 *)Irbisnxtterm((int)piStack_110,(char *)(param_5 + 1));
          if (local_13c != (undefined1 *)0x0) break;
          iVar16 = Irbisnposts((int)piStack_110);
        } while (iVar16 < 1);
      }
    }
    else {
      param_5[1] = 0;
    }
    Irbisclose(piStack_110);
    uVar11 = FUN_40004208((int)local_278);
    piVar21 = &iStack_4c4;
    uVar7 = FUN_40004208((int)local_278);
    FUN_40004140(&iStack_4c8,(char *)(param_5 + 1));
    FUN_40004410(iStack_4c8,1,uVar7,piVar21);
    uVar7 = FUN_40004208(iStack_4c4);
    ppuVar24 = &puStack_4cc;
    uVar10 = FUN_40004208((int)local_278);
    uVar22 = (undefined2)uVar10;
    uVar23 = (undefined2)((uint)uVar10 >> 0x10);
    FUN_40004140(&iStack_4d0,(char *)(param_5 + 1));
    FUN_40004410(iStack_4d0,1,CONCAT22(uVar23,uVar22),(int *)ppuVar24);
    puVar8 = (undefined4 *)FUN_400043cc(puStack_4cc);
    puVar9 = (undefined4 *)FUN_400043cc((undefined *)local_278);
    iVar16 = FUN_40026d4c(puVar8,puVar9,uVar7,uVar11);
    if (iVar16 == 0) {
      ppuVar36 = &local_140;
      FUN_40004140(&iStack_4d4,(char *)(param_5 + 1));
      uVar11 = FUN_40004208(iStack_4d4);
      iVar16 = FUN_40004208((int)local_278);
      iVar16 = iVar16 + 1;
      FUN_40004140(&iStack_4d8,(char *)(param_5 + 1));
      FUN_40004410(iStack_4d8,iVar16,uVar11,(int *)ppuVar36);
      FUN_4000a9b8((int)local_140,&iStack_4dc);
      FUN_40004010((int *)&local_140,iStack_4dc);
      pcVar12 = FUN_400043cc((undefined *)local_140);
      FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
      FUN_400252c0((char *)*param_4,&DAT_400e70c8);
    }
    break;
  case 0x2c:
    FUN_40004140((int *)&puStack_49c,(char *)param_5);
    FUN_40026f28(puStack_49c,(int *)&local_278);
    pcVar12 = FUN_400043cc((undefined *)local_278);
    FUN_4000b1d0((char *)param_5,pcVar12,32000);
    local_13c = (undefined1 *)FUN_400044f4("^",(char *)local_278);
    if (local_13c == (undefined1 *)0x0) {
      FUN_40003f78((int *)&local_128);
      ppbVar28 = &pbStack_4a0;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,3,uVar11,(int *)ppbVar28);
      iStack_124 = FUN_4000ab48(pbStack_4a0,0,extraout_ECX_35);
    }
    else {
      ppuVar36 = &local_128;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,(int *)ppuVar36);
      FUN_40004410((int)local_278,3,(uint)(local_13c + -3),(int *)&pbStack_4a4);
      iStack_124 = FUN_4000ab48(pbStack_4a4,0,extraout_ECX_36);
    }
    FUN_40029500(DAT_400e7214);
    local_13c = (undefined1 *)Irbisnocc(param_1,(int)param_2,iStack_124);
    if (0 < (int)local_13c) {
      puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
      puStack_2ec = local_13c;
      do {
        if (local_128 == (uint *)0x0) {
          iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_114);
          pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,(char *)puVar5);
          FUN_40004140((int *)&local_144,pcVar12);
        }
        else {
          FUN_40003f78((int *)&local_144);
          iVar16 = FUN_40004208((int)local_128);
          if (0 < iVar16) {
            puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
            iStack_2f0 = iVar16;
            do {
              FUN_40004120((int *)&puStack_274,
                           CONCAT31((int3)((uint)local_128 >> 8),
                                    ((char *)((int)local_128 + -1))[(int)puStack_248]));
              puVar5 = (uint *)FUN_400043cc((undefined *)puStack_274);
              iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_114);
              pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,(char *)puVar5);
              FUN_40004140((int *)&puStack_4a8,pcVar12);
              FUN_40004210((int *)&local_144,puStack_4a8);
              puStack_248 = puStack_248 + 1;
              iStack_2f0 = iStack_2f0 + -1;
            } while (iStack_2f0 != 0);
            iStack_2f0 = 0;
          }
        }
        pcVar12 = FUN_400043cc((undefined *)local_144);
        FUN_400299b4(DAT_400e7214,pcVar12,puStack_114);
        puStack_114 = puStack_114 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    FUN_40028fe0(DAT_400e7214);
    if (-1 < (int)(*(undefined1 **)(DAT_400e7214 + 0xc) + -1)) {
      puStack_114 = (undefined1 *)0x0;
      puStack_2ec = *(undefined1 **)(DAT_400e7214 + 0xc);
      do {
        puStack_248 = (undefined1 *)FUN_4002993c(DAT_400e7214,(int)puStack_114);
        FUN_4002975c(DAT_400e7214,(int)puStack_114);
        puVar5 = (uint *)&DAT_400ad770;
        iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,(int)puStack_248);
        pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,(char *)puVar5);
        FUN_40029650(DAT_400e7214,(int)puStack_114,pcVar12);
        puStack_114 = puStack_114 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    if (0 < (int)local_13c) {
      puStack_2ec = local_13c;
      puStack_114 = (undefined1 *)((int)&iRam00000000 + 1);
      do {
        pcVar12 = (char *)0x0;
        iVar16 = Irbisfieldn(param_1,(int)param_2,iStack_124,1);
        Irbisfldrep(param_1,(int)param_2,iVar16,pcVar12);
        puStack_114 = puStack_114 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    if (param_5[1] == 0x44) {
      puVar6 = (undefined1 *)(*(int *)(DAT_400e7214 + 0xc) + -1);
      if (-1 < (int)puVar6) {
        do {
          puStack_114 = puVar6;
          iVar16 = 0;
          pcVar12 = (char *)FUN_4002934c(DAT_400e7214,(int)puStack_114);
          Irbisfldadd(param_1,(int)param_2,iStack_124,pcVar12,iVar16);
          puVar6 = (undefined1 *)((int)puStack_114 + -1);
        } while ((int)puStack_114 + -1 != -1);
        puStack_114 = (undefined1 *)0xffffffff;
      }
    }
    else if (-1 < *(int *)(DAT_400e7214 + 0xc) + -1) {
      puStack_114 = (undefined1 *)0x0;
      puStack_2ec = (undefined1 *)*(int *)(DAT_400e7214 + 0xc);
      do {
        iVar16 = 0;
        pcVar12 = (char *)FUN_4002934c(DAT_400e7214,(int)puStack_114);
        Irbisfldadd(param_1,(int)param_2,iStack_124,pcVar12,iVar16);
        puStack_114 = puStack_114 + 1;
        puStack_2ec = (undefined1 *)((int)puStack_2ec + -1);
      } while (puStack_2ec != (undefined1 *)0x0);
      puStack_2ec = (undefined1 *)0x0;
    }
    break;
  case 0x2e:
    func_0x4008e228();
    break;
  case 0x30:
    FUN_40004140((int *)&local_128,(char *)(param_5 + 1));
    FUN_40021570((undefined *)local_128,&pOStack_600);
    FUN_40020554(pOStack_600,&pOStack_5fc);
    FUN_40021554((int *)pOStack_5fc,&local_5f8);
    FUN_40004010((int *)&local_128,local_5f8);
    pcVar12 = FUN_400043cc((undefined *)local_128);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x31:
    FUN_40004140((int *)&local_278,(char *)param_5);
    ppbVar28 = &pbStack_59c;
    uVar11 = FUN_40004208((int)local_278);
    FUN_40004410((int)local_278,2,uVar11,(int *)ppbVar28);
    local_13c = (undefined1 *)FUN_4000ab48(pbStack_59c,6,extraout_ECX_38);
    FUN_40003f78((int *)&local_278);
    if (0 < (int)local_13c) {
      puStack_2ec = local_13c;
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
      do {
        FUN_40004254((int *)&local_278,(undefined4 *)&UNK_400adb18,local_278);
        puStack_248 = puStack_248 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    uVar11 = FUN_4000ab0c((byte *)local_278);
    uVar10 = FUN_40002eb8(uVar11);
    FUN_4000aa6c(uVar10,(int *)&local_140);
    iVar16 = FUN_40004208((int)local_140);
    local_13c = local_13c + -iVar16;
    if (0 < (int)local_13c) {
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 1);
      puStack_2ec = local_13c;
      do {
        FUN_40004254((int *)&local_140,(undefined4 *)&DAT_400ad7b0,local_140);
        puStack_248 = puStack_248 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x32:
    FUN_400252c0((char *)param_5,&DAT_400e6ec8);
    FUN_40004140((int *)&local_278,(char *)param_5);
    FUN_40003f78((int *)&local_140);
    local_13c = (undefined1 *)0x2;
    uVar18 = false;
    uVar19 = true;
    puStack_260 = (undefined1 *)0x0;
    do {
      FUN_40004410((int)local_278,(int)local_13c,1,(int *)&local_128);
      FUN_40004318(local_128,(uint *)&DAT_400ad7b0);
      if (((bool)uVar18) ||
         (FUN_40004318(local_128,(uint *)&UNK_400adb18), !(bool)uVar18 && !(bool)uVar19)) {
        FUN_40004318(local_128,(uint *)&UNK_400ad73c);
        if (((bool)uVar19) || (FUN_40004318(local_128,(uint *)&UNK_400adb54), (bool)uVar19)) {
          FUN_4000aa6c(DAT_400e71e8,(int *)&local_140);
          FUN_40003f78((int *)&local_128);
        }
        puStack_260 = (undefined1 *)((int)&iRam00000000 + 1);
      }
      else {
        local_13c = local_13c + 1;
      }
      uVar18 = puStack_260 == (undefined1 *)0x0;
      uVar19 = puStack_260 == (undefined1 *)((int)&iRam00000000 + 1);
    } while (!(bool)uVar19);
    FUN_40004410((int)local_278,2,(uint)(local_13c + -2),(int *)&local_128);
    local_13c = local_13c + -1;
    while (bVar20 = local_128 == (uint *)0x0, !bVar20) {
      FUN_40004318(local_128,(uint *)&DAT_400ad7b0);
      if (bVar20) {
        DAT_400e71e8 = (undefined1 *)0x0;
      }
      else {
        FUN_40004318(local_128,(uint *)&UNK_400ad73c);
        if (bVar20) {
          FUN_4000aa6c(DAT_400e71e8,(int *)&local_140);
        }
        else {
          FUN_40004318(local_128,(uint *)&UNK_400adb0c);
          if (bVar20) {
            if (((int)DAT_400e71e8 < 0x10) && (0 < (int)DAT_400e71e8)) {
              FUN_400041ac((int *)&local_140,(byte *)((int)DAT_400e71e8 * 0x100 + 0x400e2190));
            }
            else {
              FUN_40003f78((int *)&local_140);
            }
          }
          else {
            iVar16 = FUN_4000ab48((byte *)local_128,0,extraout_ECX_37);
            DAT_400e71e8 = DAT_400e71e8 + iVar16;
          }
        }
      }
      local_13c = local_13c + 1;
      FUN_40004410((int)local_278,(int)local_13c,1,(int *)&local_128);
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x33:
    FUN_40003f78((int *)&local_140);
    FUN_40004140((int *)&puStack_5a8,(char *)param_5);
    FUN_400237a8(puStack_5a8,(int *)&local_278);
    pcVar12 = FUN_400043cc((undefined *)local_278);
    FUN_40087f50((int *)&param_5,pcVar12,(uint *)&DAT_400e7210);
    iVar16 = FUN_4000b140((char *)param_5);
    local_13c = (undefined1 *)(iVar16 + -1);
    if (1 < (int)local_13c) {
      puStack_2ec = (undefined1 *)(iVar16 + -2);
      puStack_248 = (undefined1 *)((int)&iRam00000000 + 2);
      do {
        if ((byte)(param_5[(int)puStack_248] + 0x40) < 0x20) {
          FUN_400041ac((int *)&local_128,(byte *)((uint)param_5[(int)puStack_248] * 6 + 0x400e1d50))
          ;
          FUN_40004410((int)local_128,1,1,(int *)&puStack_5b0);
          pcVar12 = FUN_400043cc(puStack_5b0);
          pcVar12 = (char *)FUN_400252c0(pcVar12,&DAT_400e6ec8);
          FUN_40004140(&iStack_5ac,pcVar12);
          ppuVar36 = &puStack_5b4;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,2,uVar11,(int *)ppuVar36);
          puVar5 = puStack_5b4;
          FUN_400042c8((int *)&local_140,3);
        }
        else if ((byte)(param_5[(int)puStack_248] + 0x20) < 0x20) {
          FUN_400041ac((int *)&puStack_5b8,
                       (byte *)((uint)param_5[(int)puStack_248] * 6 + 0x400e1c90));
          FUN_40004210((int *)&local_140,puStack_5b8);
        }
        else if (param_5[(int)puStack_248] != 0x22) {
          FUN_40004120((int *)&puStack_5bc,
                       CONCAT31((int3)((uint)param_5 >> 8),param_5[(int)puStack_248]));
          FUN_40004210((int *)&local_140,puStack_5bc);
        }
        puStack_248 = puStack_248 + 1;
        puStack_2ec = puStack_2ec + -1;
      } while (puStack_2ec != (undefined1 *)0x0);
    }
    FUN_40023740((undefined *)local_140,&iStack_5c0);
    FUN_40004010((int *)&local_140,iStack_5c0);
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x34:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    pcVar32 = "";
    iVar16 = Irbisfieldn(param_1,(int)param_2,0x65,1);
    pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,pcVar32);
    FUN_40004140((int *)&local_128,pcVar12);
    FUN_40029500(DAT_400e7218);
    if (local_128 != (uint *)0x0) {
      uVar18 = DAT_400e71cc == (int *)0x0;
      if ((bool)uVar18) {
code_r0x400a34be:
        FUN_40004140((int *)&puStack_4f8,*(char **)((int)param_1 + 0x7da));
        FUN_4000aea0(puStack_4f8,(int *)&puStack_4f4);
        FUN_40004210((int *)&puStack_4f4,(undefined4 *)&UNK_400adb88);
        FUN_40004140((int *)&puStack_500,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(puStack_500,(int *)&puStack_4fc);
        FUN_40026010(puStack_4fc,puStack_4f4,DAT_400e71f8,(int)pcVar32);
      }
      else {
        (**(code **)*DAT_400e71cc)(DAT_400e71cc,&DAT_400adb78,"DepositPriority");
        FUN_40004318(puStack_4e0,(uint *)&DAT_400adb24);
        if (!(bool)uVar18) goto code_r0x400a34be;
        FUN_40004140((int *)&puStack_4e8,*(char **)((int)param_1 + 0x7da));
        FUN_4000aea0(puStack_4e8,&iStack_4e4);
        FUN_40004210(&iStack_4e4,(undefined4 *)&UNK_400adb88);
        uVar22 = (undefined2)iStack_4e4;
        uVar23 = (undefined2)((uint)iStack_4e4 >> 0x10);
        FUN_40004140((int *)&puStack_4f0,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(puStack_4f0,&iStack_4ec);
        func_0x4002650c(iStack_4ec,CONCAT22(uVar23,uVar22),DAT_400e71f8);
      }
      if ((0 < *(int *)(DAT_400e7218 + 0xc)) && (0 < *(int *)(DAT_400e7218 + 0xc))) {
        local_13c = (undefined1 *)0x0;
        do {
          pcVar12 = (char *)FUN_4002934c(DAT_400e7218,(int)local_13c);
          FUN_40004140((int *)&pcStack_504,pcVar12);
          iVar16 = FUN_4000a844((char *)local_128,pcStack_504);
          if (iVar16 == 0) {
            puStack_248 = local_13c;
            break;
          }
          local_13c = local_13c + 2;
        } while ((int)local_13c < *(int *)(DAT_400e7218 + 0xc));
        if ((int)(local_13c + 1) < *(int *)(DAT_400e7218 + 0xc)) {
          FUN_40004140((int *)&puStack_508,*(char **)((int)param_1 + 0x7da));
          FUN_4000aea0(puStack_508,(int *)&local_128);
          pcVar12 = (char *)FUN_4002934c(DAT_400e7218,(int)(local_13c + 1));
          FUN_40004140((int *)&puStack_274,pcVar12);
          uVar18 = DAT_400e71cc == (int *)0x0;
          if (!(bool)uVar18) {
            (**(code **)*DAT_400e71cc)(DAT_400e71cc,&DAT_400adb78,"DepositPriority");
            FUN_40004318(puStack_50c,(uint *)&DAT_400adb24);
            if ((bool)uVar18) {
              FUN_40004140((int *)&puStack_514,*(char **)((int)param_1 + 0x7da));
              FUN_4000afc4(puStack_514,&iStack_510);
              FUN_40004254(&iStack_518,local_128,puStack_274);
              func_0x4002650c(iStack_510,iStack_518,DAT_400e71f8);
              goto code_r0x400a3711;
            }
          }
          iVar16 = DAT_400e7218;
          FUN_40004140((int *)&puStack_520,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_520,(int *)&puStack_51c);
          FUN_40004254((int *)&puStack_524,local_128,puStack_274);
          FUN_40026010(puStack_51c,puStack_524,DAT_400e71f8,iVar16);
        }
        else {
          FUN_40029500(DAT_400e7218);
        }
      }
    }
code_r0x400a3711:
    if (*(int *)(DAT_400e7218 + 0xc) < 1) {
      func_0x4009891c(0,local_278,0);
      FUN_40004010((int *)&local_140,iStack_534);
    }
    else {
      if (-1 < (int)(*(undefined1 **)(DAT_400e7218 + 0xc) + -1)) {
        local_13c = (undefined1 *)0x0;
        puStack_2ec = *(undefined1 **)(DAT_400e7218 + 0xc);
        do {
          pcVar12 = (char *)FUN_4002934c(DAT_400e7218,(int)local_13c);
          FUN_40004140((int *)&puStack_52c,pcVar12);
          FUN_40023740(puStack_52c,(int *)&puStack_528);
          pcVar12 = FUN_400043cc(puStack_528);
          FUN_40029650(DAT_400e7218,(int)local_13c,pcVar12);
          FUN_4002975c(DAT_400e7218,(int)(local_13c + 1));
          local_13c = local_13c + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      func_0x4009891c(DAT_400e7218,local_278,0);
      FUN_40004010((int *)&local_140,iStack_530);
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x35:
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    pcVar32 = "";
    iVar16 = Irbisfieldn(param_1,(int)param_2,0x65,1);
    pcVar12 = (char *)Irbisfield(param_1,(int)param_2,iVar16,pcVar32);
    FUN_40004140((int *)&local_128,pcVar12);
    FUN_40029500(DAT_400e7218);
    if (local_128 != (uint *)0x0) {
      uVar18 = DAT_400e71cc == (int *)0x0;
      if ((bool)uVar18) {
code_r0x400a3934:
        FUN_40004140((int *)&puStack_550,*(char **)((int)param_1 + 0x7da));
        FUN_4000aea0(puStack_550,(int *)&puStack_54c);
        FUN_40004210((int *)&puStack_54c,(undefined4 *)&UNK_400adb88);
        FUN_40004140((int *)&puStack_558,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(puStack_558,(int *)&puStack_554);
        FUN_40026010(puStack_554,puStack_54c,DAT_400e71f8,(int)pcVar32);
      }
      else {
        (**(code **)*DAT_400e71cc)(DAT_400e71cc,&DAT_400adb78,"DepositPriority");
        FUN_40004318(puStack_538,(uint *)&DAT_400adb24);
        if (!(bool)uVar18) goto code_r0x400a3934;
        FUN_40004140((int *)&puStack_540,*(char **)((int)param_1 + 0x7da));
        FUN_4000aea0(puStack_540,&iStack_53c);
        FUN_40004210(&iStack_53c,(undefined4 *)&UNK_400adb88);
        uVar22 = (undefined2)iStack_53c;
        uVar23 = (undefined2)((uint)iStack_53c >> 0x10);
        FUN_40004140((int *)&puStack_548,*(char **)((int)param_1 + 0x7da));
        FUN_4000afc4(puStack_548,&iStack_544);
        func_0x4002650c(iStack_544,CONCAT22(uVar23,uVar22),DAT_400e71f8);
      }
      if ((0 < *(int *)(DAT_400e7218 + 0xc)) && (0 < *(int *)(DAT_400e7218 + 0xc))) {
        local_13c = (undefined1 *)0x0;
        do {
          pcVar12 = (char *)FUN_4002934c(DAT_400e7218,(int)local_13c);
          FUN_40004140((int *)&pcStack_55c,pcVar12);
          iVar16 = FUN_4000a844((char *)local_128,pcStack_55c);
          if (iVar16 == 0) {
            puStack_248 = local_13c;
            break;
          }
          local_13c = local_13c + 2;
        } while ((int)local_13c < *(int *)(DAT_400e7218 + 0xc));
        if ((int)(local_13c + 1) < *(int *)(DAT_400e7218 + 0xc)) {
          FUN_40004140((int *)&puStack_560,*(char **)((int)param_1 + 0x7da));
          FUN_4000aea0(puStack_560,(int *)&local_128);
          pcVar12 = (char *)FUN_4002934c(DAT_400e7218,(int)(local_13c + 1));
          FUN_40004140((int *)&puStack_274,pcVar12);
          uVar18 = DAT_400e71cc == (int *)0x0;
          if (!(bool)uVar18) {
            (**(code **)*DAT_400e71cc)(DAT_400e71cc,&DAT_400adb78,"DepositPriority");
            FUN_40004318(puStack_564,(uint *)&DAT_400adb24);
            if ((bool)uVar18) {
              FUN_40004140((int *)&puStack_56c,*(char **)((int)param_1 + 0x7da));
              FUN_4000afc4(puStack_56c,&iStack_568);
              FUN_40004254(&iStack_570,local_128,puStack_274);
              func_0x4002650c(iStack_568,iStack_570,DAT_400e71f8);
              goto code_r0x400a3b87;
            }
          }
          iVar16 = DAT_400e7218;
          FUN_40004140((int *)&puStack_578,*(char **)((int)param_1 + 0x7da));
          FUN_4000afc4(puStack_578,(int *)&puStack_574);
          FUN_40004254((int *)&puStack_57c,local_128,puStack_274);
          FUN_40026010(puStack_574,puStack_57c,DAT_400e71f8,iVar16);
        }
        else {
          FUN_40029500(DAT_400e7218);
        }
      }
    }
code_r0x400a3b87:
    if (*(int *)(DAT_400e7218 + 0xc) < 1) {
      func_0x4009891c(0,local_278,0);
      FUN_40004010((int *)&local_140,iStack_58c);
    }
    else {
      if (-1 < (int)(*(undefined1 **)(DAT_400e7218 + 0xc) + -1)) {
        local_13c = (undefined1 *)0x0;
        puStack_2ec = *(undefined1 **)(DAT_400e7218 + 0xc);
        do {
          pcVar12 = (char *)FUN_4002934c(DAT_400e7218,(int)local_13c);
          FUN_40004140((int *)&puStack_584,pcVar12);
          FUN_40023740(puStack_584,(int *)&puStack_580);
          pcVar12 = FUN_400043cc(puStack_580);
          FUN_40029650(DAT_400e7218,(int)local_13c,pcVar12);
          FUN_4002975c(DAT_400e7218,(int)(local_13c + 1));
          local_13c = local_13c + 1;
          puStack_2ec = puStack_2ec + -1;
        } while (puStack_2ec != (undefined1 *)0x0);
      }
      func_0x4009891c(DAT_400e7218,local_278,0);
      FUN_40004010((int *)&local_140,iStack_588);
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x36:
    FUN_40004010((int *)&local_140,0x400ad7b0);
    FUN_400252c0((char *)param_5,&DAT_400e6ec8);
    FUN_40004140((int *)&local_278,(char *)(param_5 + 1));
    local_13c = (undefined1 *)FUN_400044f4(",",(char *)local_278);
    if (local_13c != (undefined1 *)0x0) {
      FUN_40004410((int)local_278,1,(uint)(local_13c + -1),&local_590);
      FUN_400042c8((int *)&local_128,3);
      piVar21 = &local_598;
      uVar11 = FUN_40004208((int)local_278);
      FUN_40004410((int)local_278,(int)(local_13c + 1),uVar11,piVar21);
      FUN_40023814(local_598,&local_594);
      FUN_400042c8((int *)&local_278,3);
      iVar16 = FUN_400044f4((char *)local_128,(char *)local_278);
      if (iVar16 != 0) {
        FUN_40004010((int *)&local_140,0x400adb24);
      }
    }
    pcVar12 = FUN_400043cc((undefined *)local_140);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x37:
    FUN_40004140((int *)&local_128,(char *)(param_5 + 1));
    do {
      puStack_260 = (undefined1 *)FUN_400044f4("<",(char *)local_128);
      if (0 < (int)puStack_260) {
        ppcVar33 = &pcStack_5ec;
        local_13c = puStack_260;
        uVar11 = FUN_40004208((int)local_128);
        FUN_40004410((int)local_128,(int)(puStack_260 + 1),uVar11,(int *)ppcVar33);
        puStack_260 = (undefined1 *)FUN_400044f4(">",pcStack_5ec);
        if (0 < (int)puStack_260) {
          ppuVar38 = &puStack_5f0;
          uVar11 = FUN_40004208((int)local_128);
          FUN_40004410((int)local_128,(int)(local_13c + (int)puStack_260 + 1),uVar11,(int *)ppuVar38
                      );
          puVar8 = puStack_5f0;
          FUN_40004410((int)local_128,1,(uint)(local_13c + -1),(int *)&puStack_5f4);
          FUN_40004254((int *)&local_128,puStack_5f4,puVar8);
        }
      }
    } while (puStack_260 != (undefined1 *)0x0);
    pcVar12 = FUN_400043cc((undefined *)local_128);
    FUN_40087f50((int *)param_4,pcVar12,(uint *)&DAT_400e7210);
    break;
  case 0x38:
    func_0x4008de78();
    break;
  case 0x39:
    func_0x40098f74();
    break;
  case 0x3a:
    DAT_400e31f4 = 1;
  }
  FUN_400031f8(local_118);
  local_11c = 0;
  *in_FS_OFFSET = (int)puVar5;
  FUN_40003f9c(&local_be4,3);
  FUN_40004624(&local_bd8);
  FUN_40003f9c((int *)&local_bd4,0x10);
  FUN_40004624(&local_b94);
  FUN_40003f78(&local_b90);
  FUN_40004624(&local_b8c);
  FUN_40003f9c((int *)&local_b88,0x2e);
  FUN_4000463c(&local_ad0,2);
  FUN_40003f9c((int *)&local_ac8,0x1c);
  FUN_40003f78(&local_a50);
  FUN_40003f9c(&local_a58,2);
  FUN_40003f9c((int *)&local_a4c,0x11);
  FUN_40004624(&local_a08);
  FUN_40003f9c(&local_a04,0xc);
  FUN_40004624(&local_9d4);
  FUN_40003f9c(&local_9d0,4);
  FUN_40004624(&local_9c0);
  FUN_40003f9c((int *)&local_9bc,0x2a);
  FUN_40004624(&local_914);
  FUN_40003f9c(&local_910,0x12);
  FUN_40003f78((int *)&local_8b8);
  FUN_40003f9c((int *)&local_8c8,4);
  FUN_40003f9c((int *)&local_8b4,0x1c);
  FUN_40004624(&local_844);
  FUN_40003f9c(&local_840,0x43);
  FUN_40003f9c(&local_734,0x42);
  FUN_40003f9c(&local_61c,2);
  FUN_40004624(&local_614);
  FUN_40003f78((int *)&local_610);
  FUN_4000463c(&local_60c,5);
  FUN_40003f9c(&local_5f8,0x18);
  FUN_40003f78(&local_594);
  FUN_40003f78(&local_598);
  FUN_40003f9c(&local_590,0x34);
  FUN_4000463c(&local_4c0,4);
  FUN_40003f9c(&local_4b0,6);
  FUN_4000463c(&local_498,2);
  FUN_40003f78(&local_490);
  FUN_4000463c(&local_48c,2);
  FUN_40003f78((int *)&local_484);
  FUN_4000463c(&local_480,5);
  FUN_40003f9c((int *)&local_46c,0x1a);
  FUN_40003f9c((int *)&local_404,3);
  FUN_40003f9c((int *)&local_3f0,8);
  FUN_40003f9c((int *)&local_3c4,0xe);
  FUN_4000463c(&local_388,2);
  FUN_40003f9c(&local_380,0x19);
  FUN_40003f78((int *)&local_2d0);
  FUN_4000463c(&local_2c0,7);
  FUN_40003f78((int *)&local_2a4);
  FUN_40003f9c((int *)&local_278,4);
  FUN_40003f9c(local_254,2);
  FUN_40003f9c((int *)&local_144,2);
  FUN_40003f78((int *)&local_128);
  return;
}


