#include "formtrig/formtrig_abi.h"

#include "llvm/ADT/Statistic.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/InstrTypes.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/Module.h"
#include "llvm/Config/llvm-config.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

#if LLVM_VERSION_MAJOR >= 12
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#else
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/Pass.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"
#endif

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <string>
#include <unordered_set>
#include <vector>

using namespace llvm;

namespace {

static uint32_t hashString(const std::string &s) {
  uint32_t h = 2166136261u;
  for (char c : s) {
    h ^= static_cast<unsigned char>(c);
    h *= 16777619u;
  }
  if (!h) h = 1;
  return h;
}

static PointerType *i8PtrTy(LLVMContext &C) {
  return PointerType::getUnqual(Type::getInt8Ty(C));
}

static bool startsWith(StringRef S, StringRef Prefix) {
#if LLVM_VERSION_MAJOR >= 18
  return S.starts_with(Prefix);
#else
  return S.startswith(Prefix);
#endif
}

class FormtrigInstrumenter {
 public:
  bool runOnModule(Module &M) {
    configureInstrumentation();

    LLVMContext &C = M.getContext();
    IntegerType *I8 = Type::getInt8Ty(C);
    IntegerType *I32 = Type::getInt32Ty(C);
    IntegerType *I64 = Type::getInt64Ty(C);
    Type *VoidTy = Type::getVoidTy(C);
    PointerType *I8Ptr = i8PtrTy(C);

    ActiveVar = cast<GlobalVariable>(
        M.getOrInsertGlobal("__formtrig_active", I8));
    PreReachVar = cast<GlobalVariable>(
        M.getOrInsertGlobal("__formtrig_pre_reach_enabled", I8));
    SuppressVar = cast<GlobalVariable>(
        M.getOrInsertGlobal("__formtrig_suppress", I8));

    CmpFn = M.getOrInsertFunction("__formtrig_log_cmp_ex", VoidTy, I32, I32,
                                  I64, I64, I8, I32);
    BranchFn =
        M.getOrInsertFunction("__formtrig_log_branch", VoidTy, I32, I8);
	    MemFn = M.getOrInsertFunction("__formtrig_log_mem_access", VoidTy, I32,
	                                  I8Ptr, I64, I8, I64);
	    MemTransferFn =
	        M.getOrInsertFunction("__formtrig_log_mem_transfer", VoidTy, I32,
	                              I8Ptr, I8Ptr, I64);
	    DivFn = M.getOrInsertFunction("__formtrig_log_div", VoidTy, I32, I64);
    ModFn = M.getOrInsertFunction("__formtrig_log_mod", VoidTy, I32, I64);
    ArithFn = M.getOrInsertFunction("__formtrig_log_arith", VoidTy, I32, I32,
                                    I64, I64, I64, I32);
    FtMallocFn =
        M.getOrInsertFunction("__formtrig_malloc", I8Ptr, I64, I32);
    FtFreeFn = M.getOrInsertFunction("__formtrig_free", VoidTy, I8Ptr, I32);

    bool Changed = false;
    std::vector<CallInst *> MallocCalls;
    std::vector<CallInst *> FreeCalls;

    for (Function &F : M) {
      if (F.isDeclaration()) continue;
      if (startsWith(F.getName(), "formtrig") ||
          startsWith(F.getName(), "__formtrig"))
        continue;

      uint32_t FunctionClass = classifyFunction(F.getName());
      uint32_t InstNo = 0;
      std::vector<Instruction *> Worklist;
      for (Instruction &I : instructions(F)) Worklist.push_back(&I);
      for (Instruction *IP : Worklist) {
        if (!IP || !IP->getParent()) continue;
        Instruction &I = *IP;
        uint32_t CurInstNo = InstNo++;
        std::string Key = (F.getName().str() + ":" + std::to_string(CurInstNo));
        uint32_t SiteId = hashString(Key);

        if (InstrumentCmp && (isa<ICmpInst>(&I))) {
          auto *CI = cast<ICmpInst>(&I);
          if (!CI->getType()->isIntegerTy(1)) continue;
          if (!siteAllowed(SiteId)) continue;
          emitSiteMap(I, SiteId, CurInstNo, "cmp");
          instrumentCmp(CI, SiteId, FunctionClass);
          Changed = true;
          continue;
        }

        if (InstrumentBranch && (isa<BranchInst>(&I))) {
          auto *BI = cast<BranchInst>(&I);
          if (BI->isConditional()) {
            if (!siteAllowed(SiteId)) continue;
            emitSiteMap(I, SiteId, CurInstNo, "branch");
            instrumentBranch(BI, SiteId);
            Changed = true;
          }
          continue;
        }

        if (InstrumentMem && (isa<LoadInst>(&I))) {
          auto *LI = cast<LoadInst>(&I);
          if (!siteAllowed(SiteId)) continue;
          emitSiteMap(I, SiteId, CurInstNo, "load");
          instrumentLoad(M, LI, SiteId);
          Changed = true;
          continue;
        }

	        if (InstrumentMem && (isa<StoreInst>(&I))) {
	          auto *SI = cast<StoreInst>(&I);
	          if (!siteAllowed(SiteId)) continue;
	          emitSiteMap(I, SiteId, CurInstNo, "store");
	          instrumentStore(M, SI, SiteId);
	          Changed = true;
	          continue;
	        }

	        if (InstrumentMem && (isa<MemTransferInst>(&I))) {
	          auto *MTI = cast<MemTransferInst>(&I);
	          if (!siteAllowed(SiteId)) continue;
	          emitSiteMap(I, SiteId, CurInstNo, "memtransfer");
	          instrumentMemTransfer(MTI, SiteId);
	          Changed = true;
	          continue;
	        }

        if ((InstrumentArith || InstrumentDiv) && (isa<BinaryOperator>(&I))) {
          auto *BO = cast<BinaryOperator>(&I);
          if (!siteAllowed(SiteId)) continue;
          if (instrumentBinary(BO, SiteId)) {
            emitSiteMap(I, SiteId, CurInstNo, "binary");
            Changed = true;
          }
          continue;
        }

        if (InstrumentAlloc && (isa<CallInst>(&I))) {
          auto *Call = cast<CallInst>(&I);
	          Function *Callee = Call->getCalledFunction();
	          if (!Callee) continue;
	          StringRef Name = Callee->getName();
	          if (InstrumentMem && isMemTransferCall(Name) &&
	              Call->arg_size() >= 3) {
	            if (!siteAllowed(SiteId)) continue;
	            emitSiteMap(I, SiteId, CurInstNo, "memtransfer_call");
	            instrumentMemTransferCall(Call, SiteId);
	            Changed = true;
	          }
	          if (Name == "malloc" && Call->arg_size() == 1 &&
	              siteAllowed(hashString(callKey(Call, "malloc"))))
	            MallocCalls.push_back(Call);
	          if (Name == "free" && Call->arg_size() == 1 &&
	              siteAllowed(hashString(callKey(Call, "free"))))
	            FreeCalls.push_back(Call);
	        }
      }
    }

    for (CallInst *Call : MallocCalls) {
      rewriteMalloc(Call, hashString(callKey(Call, "malloc")));
      Changed = true;
    }
    for (CallInst *Call : FreeCalls) {
      rewriteFree(Call, hashString(callKey(Call, "free")));
      Changed = true;
    }

    return Changed;
  }

 private:
  FunctionCallee CmpFn;
	  FunctionCallee BranchFn;
	  FunctionCallee MemFn;
	  FunctionCallee MemTransferFn;
	  FunctionCallee DivFn;
  FunctionCallee ModFn;
  FunctionCallee ArithFn;
  FunctionCallee FtMallocFn;
  FunctionCallee FtFreeFn;
  GlobalVariable *ActiveVar = nullptr;
  GlobalVariable *PreReachVar = nullptr;
  GlobalVariable *SuppressVar = nullptr;
  bool InstrumentCmp = true;
  bool InstrumentBranch = false;
  bool InstrumentMem = false;
  bool InstrumentDiv = true;
  bool InstrumentArith = true;
  bool InstrumentAlloc = false;
  bool InlineGuard = true;
  bool HasSiteFilter = false;
  std::unordered_set<uint32_t> InstrumentSiteIds;

  static bool envFlag(const char *Name, bool DefaultValue) {
    const char *Value = getenv(Name);
    if (!Value || !*Value) return DefaultValue;
    if (Value[0] == '0' || Value[0] == 'n' || Value[0] == 'N' ||
        Value[0] == 'f' || Value[0] == 'F')
      return false;
    return true;
  }

  static uint32_t classifyFunction(StringRef Name) {
    if (Name.contains("malloc") || Name.contains("calloc") ||
        Name.contains("realloc") || Name.contains("alloc") ||
        Name.contains("free") || Name.contains("inflate") ||
        Name.contains("deflate") || Name.contains("zlib") ||
        Name.contains("compress") || Name.contains("decompress"))
      return 1u;
    return 0u;
  }

  void addSiteIdToken(const std::string &Token) {
    if (Token.empty()) return;
    errno = 0;
    char *End = nullptr;
    unsigned long Value = strtoul(Token.c_str(), &End, 0);
    if (errno || End == Token.c_str() || (End && *End) || Value == 0 ||
        Value > 0xfffffffful)
      return;
    InstrumentSiteIds.insert(static_cast<uint32_t>(Value));
    HasSiteFilter = true;
  }

  void parseSiteIdList(const char *Text) {
    if (!Text || !*Text) return;
    HasSiteFilter = true;
    std::string Token;
    for (const char *P = Text; *P; P++) {
      char C = *P;
      if (C == ',' || C == ';' || C == ':' || C == '\n' || C == '\r' ||
          C == '\t' || C == ' ') {
        addSiteIdToken(Token);
        Token.clear();
      } else {
        Token.push_back(C);
      }
    }
    addSiteIdToken(Token);
  }

  void loadSiteIdFile(const char *Path) {
    if (!Path || !*Path) return;
    HasSiteFilter = true;
    std::ifstream In(Path);
    if (!In) return;
    std::string Line;
    while (std::getline(In, Line)) {
      std::string Token;
      for (char C : Line) {
        if (C == '#') break;
        if (C == ',' || C == ';' || C == ':' || C == '\t' || C == ' ') {
          addSiteIdToken(Token);
          Token.clear();
        } else {
          Token.push_back(C);
        }
      }
      addSiteIdToken(Token);
    }
  }

  bool siteAllowed(uint32_t SiteId) const {
    return !HasSiteFilter || InstrumentSiteIds.count(SiteId);
  }

  void configureInstrumentation() {
    const char *LevelEnv = getenv("FORMTRIG_INSTRUMENT_LEVEL");
    std::string Level = LevelEnv && *LevelEnv ? LevelEnv : "balanced";

    if (Level == "full") {
      InstrumentCmp = true;
      InstrumentBranch = true;
      InstrumentMem = true;
      InstrumentDiv = true;
      InstrumentArith = true;
      InstrumentAlloc = true;
    } else if (Level == "balanced") {
      InstrumentCmp = true;
      InstrumentBranch = true;
      InstrumentMem = false;
      InstrumentDiv = true;
      InstrumentArith = true;
      InstrumentAlloc = false;
    } else if (Level == "tiny") {
      InstrumentCmp = true;
      InstrumentBranch = false;
      InstrumentMem = false;
      InstrumentDiv = true;
      InstrumentArith = true;
      InstrumentAlloc = false;
    } else if (Level == "slice") {
      InstrumentCmp = true;
      InstrumentBranch = false;
      InstrumentMem = true;
      InstrumentDiv = true;
      InstrumentArith = true;
      InstrumentAlloc = true;
    } else if (Level == "cmp") {
      InstrumentCmp = true;
      InstrumentBranch = false;
      InstrumentMem = false;
      InstrumentDiv = false;
      InstrumentArith = false;
      InstrumentAlloc = false;
    } else {
      InstrumentCmp = true;
      InstrumentBranch = false;
      InstrumentMem = false;
      InstrumentDiv = true;
      InstrumentArith = true;
      InstrumentAlloc = false;
    }

    InstrumentCmp = envFlag("FORMTRIG_INSTRUMENT_CMP", InstrumentCmp);
    InstrumentBranch =
        envFlag("FORMTRIG_INSTRUMENT_BRANCH", InstrumentBranch);
    InstrumentMem = envFlag("FORMTRIG_INSTRUMENT_MEM", InstrumentMem);
    InstrumentDiv = envFlag("FORMTRIG_INSTRUMENT_DIV", InstrumentDiv);
    InstrumentArith = envFlag("FORMTRIG_INSTRUMENT_ARITH", InstrumentArith);
    InstrumentAlloc = envFlag("FORMTRIG_INSTRUMENT_ALLOC", InstrumentAlloc);
    InlineGuard = envFlag("FORMTRIG_INLINE_GUARD", true);
    parseSiteIdList(getenv("FORMTRIG_INSTRUMENT_SITE_IDS"));
    loadSiteIdFile(getenv("FORMTRIG_INSTRUMENT_SITE_ID_FILE"));
  }

  static std::string callKey(CallInst *Call, const char *Kind) {
    std::string S;
    raw_string_ostream OS(S);
    OS << Kind << ":";
    if (Function *F = Call->getFunction()) OS << F->getName();
    OS << ":" << *Call;
    OS.flush();
    return S;
  }

  static std::string cleanField(std::string S) {
    for (char &C : S) {
      if (C == '\t' || C == '\n' || C == '\r') C = ' ';
    }
    return S;
  }

  void emitSiteMap(const Instruction &I, uint32_t SiteId, uint32_t InstNo,
                   StringRef Kind) {
    const char *Path = getenv("FORMTRIG_SITE_MAP");
    if (!Path || !*Path) return;

    std::ofstream OS(Path, std::ios::app);
    if (!OS) return;

    std::string File = "";
    if (const Module *M = I.getModule()) File = M->getSourceFileName();
    unsigned Line = 0;
    unsigned Column = 0;
    if (DebugLoc Loc = I.getDebugLoc()) {
      Line = Loc.getLine();
      Column = Loc.getCol();
    }

    std::string Opcode;
    raw_string_ostream OpcodeOS(Opcode);
    OpcodeOS << I.getOpcodeName();
    OpcodeOS.flush();

    OS << SiteId << '\t' << Kind.str() << '\t';
    if (const Function *F = I.getFunction())
      OS << cleanField(F->getName().str());
    OS << '\t' << InstNo << '\t' << cleanField(Opcode) << '\t'
       << cleanField(File) << '\t' << Line << '\t' << Column << '\n';
  }

  Value *toI64(IRBuilder<> &B, Value *V, bool Signed = false) {
    LLVMContext &C = B.getContext();
    IntegerType *I64 = Type::getInt64Ty(C);
    Type *Ty = V->getType();

    if (Ty->isIntegerTy()) {
      IntegerType *ITy = cast<IntegerType>(Ty);
      if (ITy->getBitWidth() == 64) return V;
      if (ITy->getBitWidth() > 64) return B.CreateTrunc(V, I64);
      return Signed ? B.CreateSExt(V, I64) : B.CreateZExt(V, I64);
    }

    if (Ty->isPointerTy()) return B.CreatePtrToInt(V, I64);

    return ConstantInt::get(I64, 0);
  }

  Value *toI8(IRBuilder<> &B, Value *V) {
    IntegerType *I8 = Type::getInt8Ty(B.getContext());
    if (V->getType()->isIntegerTy(8)) return V;
    if (V->getType()->isIntegerTy(1)) return B.CreateZExt(V, I8);
    if (V->getType()->isIntegerTy()) return B.CreateTrunc(V, I8);
    return ConstantInt::get(I8, 0);
  }

  Value *shouldLog(IRBuilder<> &B) {
    IntegerType *I8 = Type::getInt8Ty(B.getContext());
    LoadInst *Active = B.CreateLoad(I8, ActiveVar);
    Active->setVolatile(true);
    LoadInst *PreReach = B.CreateLoad(I8, PreReachVar);
    PreReach->setVolatile(true);
    LoadInst *Suppress = B.CreateLoad(I8, SuppressVar);
    Suppress->setVolatile(true);
    Value *ActiveSet = B.CreateICmpNE(Active, ConstantInt::get(I8, 0));
    Value *PreReachSet = B.CreateICmpNE(PreReach, ConstantInt::get(I8, 0));
    Value *SuppressSet = B.CreateICmpNE(Suppress, ConstantInt::get(I8, 0));
    return B.CreateAnd(B.CreateOr(ActiveSet, PreReachSet),
                       B.CreateNot(SuppressSet));
  }

  void guardedCall(IRBuilder<> &B, FunctionCallee Fn, ArrayRef<Value *> Args) {
    if (!InlineGuard) {
      B.CreateCall(Fn, Args);
      return;
    }
    BasicBlock::iterator It = B.GetInsertPoint();
    BasicBlock *BB = B.GetInsertBlock();
    if (!BB || It == BB->end()) {
      B.CreateCall(Fn, Args);
      return;
    }
    Instruction *InsertPt = &*It;
    Value *Cond = shouldLog(B);
    Instruction *ThenTerm = SplitBlockAndInsertIfThen(Cond, InsertPt, false);
    IRBuilder<> ThenB(ThenTerm);
    ThenB.CreateCall(Fn, Args);
  }

  bool isSignedPredicate(ICmpInst::Predicate Pred) {
    return Pred == ICmpInst::ICMP_SGT || Pred == ICmpInst::ICMP_SGE ||
           Pred == ICmpInst::ICMP_SLT || Pred == ICmpInst::ICMP_SLE;
  }

  void instrumentCmp(ICmpInst *CI, uint32_t SiteId, uint32_t SiteClass) {
    Instruction *InsertPt = CI->getNextNode();
    if (!InsertPt) return;
    IRBuilder<> B(InsertPt);
    bool Signed = isSignedPredicate(CI->getPredicate());
    Value *Lhs = toI64(B, CI->getOperand(0), Signed);
    Value *Rhs = toI64(B, CI->getOperand(1), Signed);
    Value *Outcome = B.CreateZExt(CI, Type::getInt8Ty(B.getContext()));
    guardedCall(B, CmpFn,
                {B.getInt32(SiteId), B.getInt32((uint32_t)CI->getPredicate()),
                 Lhs, Rhs, Outcome, B.getInt32(SiteClass)});
  }

  void instrumentBranch(BranchInst *BI, uint32_t SiteId) {
    IRBuilder<> B(BI);
    Value *Outcome = toI8(B, BI->getCondition());
    guardedCall(B, BranchFn, {B.getInt32(SiteId), Outcome});
  }

  void instrumentLoad(Module &M, LoadInst *LI, uint32_t SiteId) {
    Value *Ptr = LI->getPointerOperand();
    if (Ptr->getType()->isPointerTy() == false) return;
    Instruction *InsertPt = LI->getNextNode();
    if (!InsertPt) return;
    IRBuilder<> B(InsertPt);
    const DataLayout &DL = M.getDataLayout();
    uint64_t Size = DL.getTypeStoreSize(LI->getType());
    Value *Ptr8 = B.CreateBitCast(Ptr, i8PtrTy(B.getContext()));
    Value *Loaded = toI64(B, LI, false);
    guardedCall(B, MemFn, {B.getInt32(SiteId), Ptr8, B.getInt64(Size),
                           B.getInt8(0), Loaded});
  }

	  void instrumentStore(Module &M, StoreInst *SI, uint32_t SiteId) {
    Value *Ptr = SI->getPointerOperand();
    if (Ptr->getType()->isPointerTy() == false) return;
    IRBuilder<> B(SI);
    const DataLayout &DL = M.getDataLayout();
    uint64_t Size = DL.getTypeStoreSize(SI->getValueOperand()->getType());
    Value *Ptr8 = B.CreateBitCast(Ptr, i8PtrTy(B.getContext()));
    Value *Stored = toI64(B, SI->getValueOperand(), false);
	    guardedCall(B, MemFn, {B.getInt32(SiteId), Ptr8, B.getInt64(Size),
	                           B.getInt8(1), Stored});
	  }

	  bool isMemTransferCall(StringRef Name) {
    return Name == "memcpy" || Name == "memmove" || Name == "bcopy" ||
           startsWith(Name, "memcpy@") || startsWith(Name, "memmove@");
  }

	  void instrumentMemTransfer(MemTransferInst *MTI, uint32_t SiteId) {
	    IRBuilder<> B(MTI);
	    Value *Dst = B.CreateBitCast(MTI->getRawDest(),
	                                 i8PtrTy(B.getContext()));
	    Value *Src = B.CreateBitCast(MTI->getRawSource(),
	                                 i8PtrTy(B.getContext()));
	    Value *Len = toI64(B, MTI->getLength(), false);
	    guardedCall(B, MemTransferFn, {B.getInt32(SiteId), Dst, Src, Len});
	  }

	  void instrumentMemTransferCall(CallInst *Call, uint32_t SiteId) {
	    IRBuilder<> B(Call);
	    Value *DstArg = Call->getArgOperand(0);
	    Value *SrcArg = Call->getArgOperand(1);
	    if (!DstArg->getType()->isPointerTy() || !SrcArg->getType()->isPointerTy())
	      return;
	    Value *Dst =
	        B.CreateBitCast(DstArg, i8PtrTy(B.getContext()));
	    Value *Src =
	        B.CreateBitCast(SrcArg, i8PtrTy(B.getContext()));
	    Value *Len = toI64(B, Call->getArgOperand(2), false);
	    guardedCall(B, MemTransferFn, {B.getInt32(SiteId), Dst, Src, Len});
	  }

  bool instrumentBinary(BinaryOperator *BO, uint32_t SiteId) {
    unsigned Op = BO->getOpcode();
    if (Op != Instruction::Add && Op != Instruction::Sub &&
        Op != Instruction::Mul && Op != Instruction::UDiv &&
        Op != Instruction::SDiv && Op != Instruction::URem &&
        Op != Instruction::SRem)
      return false;

    Type *Ty = BO->getType();
    if (!Ty->isIntegerTy()) return false;
    unsigned BitWidth = cast<IntegerType>(Ty)->getBitWidth();
    if (BitWidth == 0) return false;

    if (Op == Instruction::UDiv || Op == Instruction::SDiv ||
        Op == Instruction::URem || Op == Instruction::SRem) {
      if (!InstrumentDiv) return false;
      IRBuilder<> B(BO);
      bool Signed = Op == Instruction::SDiv || Op == Instruction::SRem;
      Value *Divisor = toI64(B, BO->getOperand(1), Signed);
      if (Op == Instruction::UDiv || Op == Instruction::SDiv)
        guardedCall(B, DivFn, {B.getInt32(SiteId), Divisor});
      else
        guardedCall(B, ModFn, {B.getInt32(SiteId), Divisor});
      return true;
    }

    if (!InstrumentArith) return false;

    Instruction *InsertPt = BO->getNextNode();
    if (!InsertPt) return false;
    IRBuilder<> B(InsertPt);
    uint32_t FtOpcode = Op == Instruction::Add ? 1u
                       : Op == Instruction::Sub ? 2u
                                                : 3u;
    Value *Lhs = toI64(B, BO->getOperand(0), false);
    Value *Rhs = toI64(B, BO->getOperand(1), false);
    Value *Result = toI64(B, BO, false);
    guardedCall(B, ArithFn, {B.getInt32(SiteId), B.getInt32(FtOpcode), Lhs,
                             Rhs, Result, B.getInt32(BitWidth)});
    return true;
  }

  void rewriteMalloc(CallInst *Call, uint32_t SiteId) {
    IRBuilder<> B(Call);
    Value *Size = toI64(B, Call->getArgOperand(0), false);
    CallInst *NewCall = B.CreateCall(FtMallocFn, {Size, B.getInt32(SiteId)});
    NewCall->setCallingConv(Call->getCallingConv());
    Value *Replacement = NewCall;
    if (Call->getType() != NewCall->getType())
      Replacement = B.CreateBitCast(NewCall, Call->getType());
    Call->replaceAllUsesWith(Replacement);
    Call->eraseFromParent();
  }

  void rewriteFree(CallInst *Call, uint32_t SiteId) {
    IRBuilder<> B(Call);
    Value *Ptr = Call->getArgOperand(0);
    if (!Ptr->getType()->isPointerTy())
      Ptr = ConstantPointerNull::get(i8PtrTy(B.getContext()));
    else
      Ptr = B.CreateBitCast(Ptr, i8PtrTy(B.getContext()));
    B.CreateCall(FtFreeFn, {Ptr, B.getInt32(SiteId)});
    Call->eraseFromParent();
  }
};

}  // namespace

#if LLVM_VERSION_MAJOR >= 12
namespace {

class FormtrigNewPass : public PassInfoMixin<FormtrigNewPass> {
 public:
  PreservedAnalyses run(Module &M, ModuleAnalysisManager &) {
    FormtrigInstrumenter Instrumenter;
    bool Changed = Instrumenter.runOnModule(M);
    return Changed ? PreservedAnalyses::none() : PreservedAnalyses::all();
  }
};

}  // namespace

extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
  return {
      LLVM_PLUGIN_API_VERSION, "formtrig", LLVM_VERSION_STRING,
      [](PassBuilder &PB) {
        PB.registerPipelineStartEPCallback(
            [](ModulePassManager &MPM, OptimizationLevel) {
              MPM.addPass(FormtrigNewPass());
            });
        PB.registerPipelineParsingCallback(
            [](StringRef Name, ModulePassManager &MPM,
               ArrayRef<PassBuilder::PipelineElement>) {
              if (Name != "formtrig") return false;
              MPM.addPass(FormtrigNewPass());
              return true;
            });
      }};
}

#else
namespace {

class FormtrigPass : public ModulePass {
 public:
  static char ID;
  FormtrigPass() : ModulePass(ID) {}

  bool runOnModule(Module &M) override {
    FormtrigInstrumenter Instrumenter;
    return Instrumenter.runOnModule(M);
  }
};

}  // namespace

char FormtrigPass::ID = 0;

static RegisterPass<FormtrigPass> X("formtrig",
                                    "FORMTRIG post-reach instrumentation",
                                    false, false);

static void registerFormtrigPass(const PassManagerBuilder &,
                                 legacy::PassManagerBase &PM) {
  PM.add(new FormtrigPass());
}

static RegisterStandardPasses RegisterFormtrigOpt(
    PassManagerBuilder::EP_ModuleOptimizerEarly, registerFormtrigPass);
static RegisterStandardPasses RegisterFormtrigO0(
    PassManagerBuilder::EP_EnabledOnOptLevel0, registerFormtrigPass);
#endif
