#!/bin/bash
# Fix HACS Compliance and Push to GitHub

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  HACS Compliance Fix & Push${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "hacs.json" ]; then
    echo -e "${YELLOW}Error: Not in project directory${NC}"
    echo "Please run from: /mnt/user-data/outputs/solark_cloud_integration"
    exit 1
fi

echo -e "${GREEN}✅ Fixed HACS compliance issues:${NC}"
echo "   - Simplified hacs.json"
echo "   - Added info.md"
echo "   - Created .github structure"
echo ""

# Add files
echo -e "${GREEN}Adding files to git...${NC}"
git add hacs.json info.md .github/ HACS_COMPLIANCE.md

# Commit
echo -e "${GREEN}Creating commit...${NC}"
git commit -m "Fix HACS compliance

- Simplified hacs.json to required fields only (removed invalid fields)
- Added info.md for HACS integration display
- Created .github directory structure  
- Added HACS_COMPLIANCE.md documentation

Repository now fully HACS compliant and can be added as custom repository."

echo ""
echo -e "${GREEN}✅ Changes committed!${NC}"
echo ""
echo -e "${YELLOW}Next step: Push to GitHub${NC}"
echo -e "Run: ${GREEN}git push${NC}"
echo ""
echo -e "${YELLOW}Then in Home Assistant:${NC}"
echo "1. Open HACS → Integrations"
echo "2. Three dots → Custom repositories"
echo "3. Add: https://github.com/HammondAutomationHub/HomeAssistant_SolArk"
echo "4. Category: Integration"
echo "5. Should now work! ✨"
echo ""
